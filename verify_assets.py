"""Check declared image geometry; visual/semantic acceptance remains a viewing task."""
import argparse
import json
import math
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit('素材检查需要 Pillow：python -m pip install -r requirements.txt')


def numbers(value, length):
    return (isinstance(value, list) and len(value) == length
            and all(isinstance(n, (int, float)) and not isinstance(n, bool)
                    and math.isfinite(n) for n in value))


def inspect_assets(manifest, group=None, root=None, preview=None):
    manifest = Path(manifest)
    spec = json.loads(manifest.read_text(encoding='utf-8-sig'))
    root = Path(root) if root else manifest.parent
    errors, warnings, images, rows = [], [], {}, []
    entries = spec['files']
    if group and not any(e.get('group') == group for e in entries):
        raise ValueError(f'未知素材组：{group}')
    selected = [e for e in entries if not group or e.get('group') == group]
    for entry in selected:
        name = entry['path']
        if entry.get('kind') == 'audio' or Path(name).suffix.lower() in {'.wav', '.mp3', '.m4a'}:
            continue  # Audio validation belongs to the audio/render stage.
        try:
            with Image.open(root / name) as source:
                image = source.convert('RGBA')
                image.load()
            images[name] = image
            alpha = image.getchannel('A')
            low, high = alpha.getextrema()
            row = {'path': name, 'size': list(image.size), 'alpha_range': [low, high],
                   'visible_bbox': alpha.getbbox()}
            rows.append(row)
            expected = entry.get('size')
            if expected is not None:
                if not numbers(expected, 2) or any(n <= 0 or int(n) != n for n in expected):
                    errors.append(f'{name}: size 必须是两个正整数')
                elif list(image.size) != expected:
                    errors.append(f'{name}: 尺寸 {list(image.size)}，应为 {expected}；更新素材与构图后再修改规格')
            else:
                warnings.append(f'{name}: 未声明尺寸，不能确认它与现有坐标匹配')
            mode = entry.get('alpha')
            if mode == 'cutout' and (low != 0 or high == 0):
                errors.append(f'{name}: 切件必须同时有全透明背景和可见像素；不能用全不透明棋盘格代替透明')
            elif mode == 'opaque' and low != 255:
                errors.append(f'{name}: 净底含透明像素，会在合成中漏底')
            elif mode not in {'cutout', 'opaque', 'any', None}:
                errors.append(f'{name}: 未知 alpha 类型 {mode}')
            if high == 0:
                errors.append(f'{name}: 整张图全透明，无可见内容')
            if mode is None:
                warnings.append(f'{name}: 未声明透明要求')
            for label, box in entry.get('crops', {}).items():
                if (not numbers(box, 4) or any(int(n) != n for n in box)
                        or not (0 <= box[0] < box[2] <= image.width
                                and 0 <= box[1] < box[3] <= image.height)):
                    errors.append(f'{name}/{label}: 裁切框 {box} 越界或无效')
                elif image.crop(box).getchannel('A').getbbox() is None:
                    errors.append(f'{name}/{label}: 裁切区域没有可见内容')
        except (OSError, ValueError) as exc:
            errors.append(f'{name}: 无法读取图片 ({exc})')
    for entry in selected:
        reference = entry.get('same_canvas_as')
        if not reference or entry['path'] not in images:
            continue
        if reference not in images:
            errors.append(f"{entry['path']}: 对齐参考 {reference} 不在本次有效素材中")
        elif images[entry['path']].size != images[reference].size:
            errors.append(f"{entry['path']}: 前后姿态画布与 {reference} 不一致")

    previews, contacts_checked = [], 0
    layouts = [s for s in spec.get('layouts', []) if not group or s.get('group') == group]
    for layout in layouts:
        title = layout['id']
        size = layout.get('size')
        if not numbers(size, 2) or any(n <= 0 or int(n) != n for n in size):
            errors.append(f'{title}: 预览画布必须是两个正整数')
            continue
        placements = {}
        for layer in layout['layers']:
            name, box = layer['path'], layer.get('box')
            if name not in images:
                errors.append(f'{title}: 图层 {name} 未通过读取')
                continue
            if not numbers(box, 4) or box[2] <= 0 or box[3] <= 0:
                errors.append(f'{title}/{name}: box 必须是 [x,y,宽,高] 且宽高为正')
                continue
            if layer['id'] in placements:
                errors.append(f"{title}: 重复图层 ID {layer['id']}")
            placements[layer['id']] = (images[name], box)
        for contact in layout.get('contacts', []):
            try:
                positions = []
                for endpoint in [contact['a'], contact['b']]:
                    image, box = placements[endpoint['layer']]
                    point = endpoint['point']
                    if (not numbers(point, 2) or not
                            (0 <= point[0] < image.width and 0 <= point[1] < image.height)):
                        raise ValueError('对齐点必须位于对应源图内部')
                    if image.getpixel((int(point[0]), int(point[1])))[3] == 0:
                        raise ValueError('对齐点落在全透明像素上，请核对脚底或握点标注')
                    positions.append((box[0] + point[0] / image.width * box[2],
                                      box[1] + point[1] / image.height * box[3]))
                tolerance = contact.get('tolerance', 3)
                if (isinstance(tolerance, bool) or not isinstance(tolerance, (int, float))
                        or not math.isfinite(tolerance) or tolerance < 0):
                    raise ValueError('容差必须是有限非负像素数')
                distance = math.dist(*positions)
                contacts_checked += 1
                if distance > tolerance:
                    errors.append(f"{title}/{contact['id']}: 对齐点相距 {distance:.2f}px，超过 {tolerance}px")
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f'{title}: 对齐定义无效 ({exc})')
        if preview is not None and len(placements) == len(layout['layers']):
            output = Path(preview) / (title + '.png')
            if Path(title).name != title or title in {'.', '..'}:
                errors.append(f'{title}: 预览 ID 不能包含路径')
            elif output.exists():
                errors.append(f'{output.name}: 已存在，请使用新的预览目录')
            else:
                # Two neutral backgrounds reveal edge halos and unintentional holes.
                sheet = Image.new('RGB', (size[0] * 2, size[1]))
                for index, color in enumerate(['#ececec', '#232937']):
                    canvas = Image.new('RGBA', tuple(size), color)
                    for image, box in placements.values():
                        scaled = image.resize((max(1, round(box[2])), max(1, round(box[3]))), Image.Resampling.LANCZOS)
                        canvas.alpha_composite(scaled, (round(box[0]), round(box[1])))
                    sheet.paste(canvas.convert('RGB'), (index * size[0], 0))
                output.parent.mkdir(parents=True, exist_ok=True)
                sheet.save(output)
                previews.append(str(output))
    if not layouts:
        warnings.append('没有静态重组布局；对齐和接触尚未检查')
    elif not contacts_checked:
        warnings.append('未声明可量化接触点；重组预览中的内容位置仍需人工核对')
    return {'geometry': 'failed' if errors else 'passed', 'images': rows,
            'contacts_checked': contacts_checked, 'errors': errors, 'warnings': warnings,
            'previews': previews, 'visual_acceptance': 'not_checked',
            'limits': '只检查已声明尺寸、alpha、裁切和静态点；不识别人物、残影、棋盘格纹理或运动接触'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--group', help='只检查本次使用的素材组')
    parser.add_argument('--root', type=Path, help='图片所在根目录；默认清单所在目录')
    parser.add_argument('--preview', type=Path, help='按已声明布局输出浅/深底重组预览；不覆盖旧图')
    args = parser.parse_args(argv)
    try:
        report = inspect_assets(args.manifest, args.group, args.root, args.preview)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'素材清单无效：{exc}')
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
