import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description='Encoding checks only; not content acceptance.')
parser.add_argument('video', type=Path)
args = parser.parse_args()
if not args.video.is_file():
    raise FileNotFoundError(args.video)
probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                        '-of', 'json', str(args.video)], check=True, capture_output=True)
data = json.loads(probe.stdout)
video = [s for s in data['streams'] if s['codec_type'] == 'video']
audio = [s for s in data['streams'] if s['codec_type'] == 'audio']
if not video or not audio:
    raise ValueError('Expected both video and audio streams.')
subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(args.video),
                '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'], check=True)
keep = ['codec_type', 'codec_name', 'width', 'height', 'r_frame_rate',
        'sample_rate', 'channels', 'start_time', 'duration']
print(json.dumps({'streams': [{k: s[k] for k in keep if k in s} for s in video+audio],
                  'container_duration': data['format'].get('duration'),
                  'full_decode': 'passed', 'content_motion_listening': 'not_checked'},
                 ensure_ascii=False, indent=2))
