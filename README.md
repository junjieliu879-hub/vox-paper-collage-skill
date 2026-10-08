# Vox Paper Collage Skill

**把文案或原声，转成有纸张材质、人物道具分层和语义运镜的拼贴讲解视频。**

这是一套中文制作 Skill、完整方法文档和本地渲染工具。可交给支持文件读取及代码执行的 AI 助手使用；普通聊天界面可用它分析内容与设计分镜，不能因此自动获得制作工具。

## 开始使用

1. 下载本仓库：绿色 **Code → Download ZIP**，解压。
2. 把 `SKILL.md`、`WORKFLOW.md`、`VISUAL_GUIDE.md` 交给你的 AI 助手，再提供文案或音频、画幅和制作范围。
3. 按下方步骤验证本地渲染；随后依据全文重新设计场面和生成所需素材。

可直接发给 AI：

> 请阅读 SKILL.md、WORKFLOW.md 与 VISUAL_GUIDE.md，按我的文案/原声制作纸张拼贴视频。先理解全文关系，再写唯一分镜，验证最难停留图的含义与纸感，补齐必要切件、净底和遮挡层，分别设计人物道具运动与摄像机。不要以整图推拉、全屏噪点或统一白边代替分层剪纸。保留原声和旧版；若缺图片或执行能力，明确说明，不声称已经完成。

## 这套流程包含什么

| 内容 | 文件 |
|---|---|
| Skill 入口 | [SKILL.md](SKILL.md) |
| 从内容理解到交付的完整流程 | [WORKFLOW.md](WORKFLOW.md) |
| 纸材、提示词、切件、净底、人物道具绑定、遮挡、视差与转场 | [VISUAL_GUIDE.md](VISUAL_GUIDE.md) |
| 唯一分镜模板 | [STORYBOARD.txt](STORYBOARD.txt) |
| Canvas/Chrome → FFmpeg 渲染 | [render.mjs](render.mjs) |
| 无外部素材机制演示 | [demo.html](demo.html) |
| 郑和剪纸与通勤视差案例代码 | [case-zhenghe.html](case-zhenghe.html)、[case-commute.py](case-commute.py) |
| 案例需要的素材及角色 | [ASSETS.json](ASSETS.json) |
| 尺寸、真实透明、裁切与静态对齐检查 | [verify_assets.py](verify_assets.py) |
| 候选转写、编码检查 | [transcribe.py](transcribe.py)、[verify_video.py](verify_video.py) |
| 验证范围 | [VALIDATION.md](VALIDATION.md) |

## 本地运行

需要 Node.js 22+、Chrome/Chromium、FFmpeg/ffprobe。Pillow 路线另需 Python 3.10+ 和 Pillow。中文画面须安装中文字体。图片生成使用你实际可用的服务；本仓库没有假设存在的图片 API，也不依赖 Remotion 或视频生成模型。

```sh
npm install
node render.mjs --page demo.html --out output/demo.mp4
python verify_video.py output/demo.mp4
```

默认导出 1280×720、30fps。机制演示没有声音内容，导出时补静音轨。自带原声时加 `--audio input/voice.wav`；指定片段用 `--start 1 --end 4`；1080p 用 `--width 1920`。输出已存在会拒绝覆盖，重跑请使用新文件名。

Chrome 未自动找到时，设置 `CHROME_PATH`。PowerShell 示例：

```powershell
$env:CHROME_PATH = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
node render.mjs --page demo.html --out output/demo-new.mp4
```

打开 `demo.html` 可暂停和拖动时间；代码遵守 `window.DUR`、`window.READY`、`window.render(t)` 的取帧接口。可见纹理固定在物件上，前中后景与主体分别运动。它只演示机制，不代表真实项目的复杂版画美术质量。

准备 ASSETS.json 所列的自有素材后，可以运行历史案例代码。图片检查复用现有 Pillow 依赖；机制 demo 不需要它：

```sh
python -m pip install -r requirements.txt
node render.mjs --page case-zhenghe.html --audio input/audio.wav --assets ASSETS.json --asset-group zhenghe --out output/zhenghe.mp4
python case-commute.py --render
```

### 素材检查与对齐预览

郑和渲染命令的 `--assets` 会在取帧前检查图片；通勤案例启动时自动检查自己的素材组。无需为正常渲染另外重复单跑检查。新项目可使用自己的派生素材清单与分组；不带 `--assets` 的原有页面和纯代码 demo 仍可运行。Python 不在默认路径时，设置 `VOX_PYTHON` 为实际解释器路径。

需要定位素材问题或查看静态重组时，单独运行：

```sh
python verify_assets.py ASSETS.json --group zhenghe --preview output/assets-review-v1
python verify_assets.py ASSETS.json --group commute
```

文件缺失、尺寸不符、假透明（全不透明切件）、全透明空图、净底漏透明、裁切越界/裁空、前后姿态画布不一致会返回失败。声明了接触点时，也检查按放置框变换后的静态点距离。预览使用浅/深底且拒绝覆盖旧图；`--root` 可指定图片所在目录。

原案例尺寸已经实测填入 ASSETS.json。新主题先按唯一分镜确定实际素材和构图，再派生清单，不把案例尺寸当统一规格。字段与对齐方法见 [VISUAL_GUIDE.md](VISUAL_GUIDE.md#素材数值检查与静态重组)。检查通过不代表净底无残影、接触点选对或运动自然；没有布局或接触点会明确提示待查，不编造自动视觉验收。

检查脚本的回归测试：`python -m unittest test_verify_assets`。

仅当没有可靠转写时安装可选依赖：

```sh
python -m pip install -r requirements-asr-optional.txt
python transcribe.py input/voice.wav output/candidate.json
```

转写模型首次运行可能下载；候选时间戳需定点核听。没有提供 TTS 服务；只有文案时应先确认可用配音渠道，再锁定音频。

## 效果标准

- 不看字幕，主要人物/道具关系仍能读懂。
- 实际素材有剪纸轮廓、印刷细节与可信叠层，不能只有平滑插画加颗粒。
- 需要动作的对象真实独立于背景；移开后没有原位残影。
- 手与物件接触、人物与地面、前景遮挡和镜头覆盖正确。
- 运镜新增信息、交接重点或改善阅读；不靠无意义摇摆填时长。
- 代码成功、全量解码及抽帧，均不替代正常速度的连续视听验收。

## 公开范围与许可证

公开代码、规则、模板和素材规格。**历史案例的原声、成片、生成图片及私人交接包没有公开上传。** 因此本仓库能运行机制示例，但案例代码需要使用者自行提供素材，不承诺零素材复刻原样片。

本项目采用 [MIT](LICENSE)，并保留上游 Vox Director 的 [MIT 许可证](LICENSE-UPSTREAM) 与 [来源说明](THIRD_PARTY_NOTICES.md)。上游部分文档含云服务示例，只供参考，不是本项目默认路线。

独立项目，与 Vox Media 无隶属关系。上传问题时请附最短复现片段、输入规格及实际异常，不提交凭据或无权公开的素材。
