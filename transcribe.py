import argparse
import json
from pathlib import Path
from faster_whisper import WhisperModel

parser = argparse.ArgumentParser(description='Candidate timing only; not a listening review.')
parser.add_argument('audio', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--model', default='small')
args = parser.parse_args()
if args.output.exists():
    raise FileExistsError('Use a new version; do not replace reliable timing.')
if not args.audio.is_file():
    raise FileNotFoundError(args.audio)
model = WhisperModel(args.model, device='cpu', compute_type='int8')
segments, info = model.transcribe(str(args.audio), word_timestamps=True, vad_filter=True)
data = {'status': 'candidate_not_listened', 'language': info.language, 'segments': []}
for s in segments:
    data['segments'].append({'start': s.start, 'end': s.end, 'text': s.text,
                            'words': [{'word': w.word, 'start': w.start, 'end': w.end}
                                      for w in (s.words or [])]})
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
print(args.output)
