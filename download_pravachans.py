#!/usr/bin/env python3
"""Preview, download and tag a CSV collection. Paths are relative to config.json.

python3 download_pravachans.py --config path/to/config.json --limit 5
Add --download to download missing files and refresh metadata on existing files.
Use --overwrite to redownload individual existing files.
Use --force with --download to clear the entire output folder first.
Requires mutagen for downloads; preview uses only the Python standard library.
"""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from urllib.request import Request, urlopen

VERSE_TYPES = (
    ('gatha_number', 'Gatha', 'G'),
    ('kalash_number', 'Kalash', 'K'),
    ('shlok_number', 'Shlok', 'S'),
    ('doha_number', 'Doha', 'D'),
    ('dohra_number', 'Dohra', 'Dh'),
    ('pad_number', 'Pad', 'P'),
    ('bol_number', 'Bol', 'B'),
    ('nay_number', 'Nay', 'N'),
    ('shakti_number', 'Shakti', 'Sh'),
    ('karma_prakriti_number', 'Karma Prakriti', 'KP'),
)


def resolve_path(value, base):
    path = Path(value).expanduser()
    return path if path.is_absolute() else base / path


def serial(value):
    value = value.strip().lower()
    if not re.fullmatch(r'\d+(?:[a-z]|\(\d+\)|-\d+)?', value):
        raise ValueError(f'Invalid serial number: {value!r}')
    match = re.match(r'\d+', value)
    return f'{int(match[0]):03d}' + value[match.end():]


def reset_output(output, protected_paths):
    """Clear only a dedicated download directory, never inputs or their parents."""
    if output.is_symlink():
        raise ValueError('Cannot clear a symlinked output folder')
    destination = output.resolve()
    if destination in (Path(destination.anchor), Path.home().resolve(), Path.cwd().resolve()):
        raise ValueError(f'Cannot clear protected output folder: {destination}')
    for path in protected_paths:
        protected = path.resolve()
        if protected == destination or destination in protected.parents:
            raise ValueError(f'Output folder contains a protected input: {protected}')
    if output.exists():
        if not output.is_dir():
            raise ValueError(f'Output location is not a folder: {output}')
        shutil.rmtree(output)
        print(f'Force: deleted output folder: {output}')


def build_entries(config, rows):
    # CSV readers are single-pass iterators; suffix detection must not consume them.
    rows = list(rows)
    entries = []
    seen_tracks, seen_names = set(), set()
    adhikars = {}
    # Lettered PDF references remain visible; numeric MP3 tracks follow CSV order.
    lettered = any(re.fullmatch(r'\d+[a-z]', row['global_serial_number'].strip().lower())
                   for row in rows)
    for position, row in enumerate(rows, 1):
        label = row['global_serial_number'].strip().lower()
        if not re.fullmatch(r'\d+[a-z]?', label):
            raise ValueError(f'Invalid global serial: {label!r}')
        number = int(re.match(r'\d+', label)[0])
        formatted = serial(label)
        if number < 1 or formatted in seen_tracks:
            raise ValueError(f'Invalid or duplicate global serial: {label}')
        seen_tracks.add(formatted)
        track = position if lettered else number
        series_serial = row.get('series_serial_number', '').strip()
        name_parts = [formatted]
        title_parts = [f"{config['granth']} {formatted}"]
        adhikar = row.get('adhikar_name', '').strip()
        folder = ''
        if adhikar:
            if adhikar in ('.', '..') or any(c in adhikar for c in '/\\\x00'):
                raise ValueError(f'Invalid Adhikar name: {adhikar!r}')
            if adhikar not in adhikars:
                adhikars[adhikar] = len(adhikars) + 1
            folder = f'{adhikars[adhikar]:02d} {adhikar}'
            title_parts.append(adhikar)
        verse_titles = []
        if series_serial:
            name_parts.append(serial(series_serial))
        for column, label, prefix in VERSE_TYPES:
            value = row.get(column, '').strip()
            if not value:
                continue
            if not re.fullmatch(r'[0-9.,()\- ]+', value):
                raise ValueError(f'Track {track}: invalid {column}: {value!r}')
            value = value.replace(' ', '')
            verse_titles.append(f'{label} {value}')
            name_parts.append(prefix + value)
        filename = '_'.join(name_parts) + '.mp3'
        if verse_titles:
            title_parts.append(' '.join(verse_titles))
        elif row.get('content_note', '').strip():
            title_parts.append(row['content_note'].strip())
        if row.get('additional_verse', '').strip():
            title_parts.append(row['additional_verse'].strip())
        if filename in seen_names:
            raise ValueError(f'Duplicate filename: {filename}')
        seen_names.add(filename)
        url = row['download_url'].strip()
        if not url.startswith(('https://', 'http://')):
            raise ValueError(f'Track {track}: invalid download URL')
        date = row.get('date', '').strip()
        if date:
            from datetime import date as date_type
            date_type.fromisoformat(date)
        entries.append(dict(track=track, filename=filename,
                            title=' - '.join(title_parts), url=url, date=date,
                            folder=folder, adhikar_name=adhikar,
                            series=row.get('series', '').strip(),
                            series_serial=series_serial))
    return entries


def tag_mp3(path, entry, config, cover):
    from mutagen.mp3 import MP3
    from mutagen.id3 import (TIT2, TPE1, TALB, TPE2, TCOM, TCON,
                             TRCK, TDRC, TXXX, COMM, APIC)

    audio = MP3(path)
    if audio.tags is None:
        audio.add_tags()
    tags = audio.tags
    for frame, value in (
        (TIT2, entry['title']), (TPE1, config['artist']),
        (TALB, config['album']), (TPE2, config['album_artist']),
        (TCOM, config['author']), (TCON, config['genre']),
        (TRCK, str(entry['track'])),
    ):
        tags.add(frame(encoding=3, text=[value]))
    if entry['date']:
        tags.add(TDRC(encoding=3, text=[entry['date']]))
    tags.add(TXXX(encoding=3, desc='Granth Author', text=[config['author']]))
    if config.get('commentator', '').strip():
        tags.add(TXXX(encoding=3, desc='Commentator', text=[config['commentator']]))
    tags.add(TXXX(encoding=3, desc='Original Series', text=[entry['series']]))
    if entry.get('adhikar_name'):
        tags.add(TXXX(encoding=3, desc='Adhikar', text=[entry['adhikar_name']]))
    tags.add(TXXX(encoding=3, desc='Series Serial Number',
                  text=[entry['series_serial']]))
    tags.add(COMM(encoding=3, lang='eng', desc='Collection', text=[
        f"Series: {entry['series']}; Pravachan: {entry['series_serial']}"
    ]))
    image = cover.read_bytes()
    if image.startswith(b'\xff\xd8\xff'):
        mime = 'image/jpeg'
    elif image.startswith(b'\x89PNG\r\n\x1a\n'):
        mime = 'image/png'
    else:
        raise ValueError('Cover must be a JPEG or PNG image')
    tags.delall('APIC')
    tags.add(APIC(encoding=3, mime=mime, type=3, desc='Cover', data=image))
    audio.save()
    check = MP3(path)
    if str(check.tags['TRCK']) != str(entry['track']) or not check.tags.getall('APIC'):
        raise RuntimeError('Metadata verification failed')


def download_entry(entry, output, cover, config, overwrite=False):
    output = output / entry.get('folder', '')
    output.mkdir(parents=True, exist_ok=True)
    target = output / entry['filename']
    metadata_only = target.exists() and not overwrite
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output, suffix='.part', delete=False) as dest:
            temporary = Path(dest.name)
            if metadata_only:
                with target.open('rb') as source:
                    shutil.copyfileobj(source, dest)
            else:
                request = Request(entry['url'], headers={'User-Agent': 'media-utils/1.0'})
                with urlopen(request, timeout=60) as response:
                    while chunk := response.read(1024 * 1024):
                        dest.write(chunk)
        tag_mp3(temporary, entry, config, cover)
        os.replace(temporary, target)
        if metadata_only:
            print(f'Updated metadata (download skipped): {target.name}')
            return 'updated'
        print(f'Saved: {target.name}')
        return 'downloaded'
    except Exception as exc:
        raise RuntimeError(f"Track {entry['track']} failed: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--force', action='store_true',
                        help='Delete the entire output folder before downloading')
    parser.add_argument('--threads', type=int, default=5, help='Concurrent downloads (default: 5)')
    args = parser.parse_args()
    if args.threads < 1:
        parser.error('--threads must be positive')
    if args.force and not args.download:
        parser.error('--force requires --download')
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    config_path = args.config.expanduser().resolve()
    config = json.loads(config_path.read_text())
    for key in ('granth', 'author', 'artist', 'input_csv', 'output_location', 'album_art_file'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f'Missing config field: {key}')
    config.setdefault('album', config['granth'])
    config.setdefault('album_artist', config['artist'])
    config.setdefault('genre', 'Pravachan')
    with resolve_path(config['input_csv'], config_path.parent).open(newline='', encoding='utf-8-sig') as source:
        entries = build_entries(config, csv.DictReader(source))
    selected = entries[:args.limit] if args.limit else entries
    if not selected:
        raise ValueError('The input CSV contains no tracks; output folder was not changed')
    output = resolve_path(config['output_location'], config_path.parent)
    cover = resolve_path(config['album_art_file'], config_path.parent)
    if not cover.is_file():
        raise FileNotFoundError(cover)
    if not args.download:
        print(json.dumps({'output_location': str(output), 'album': config['album'],
                          'artist': config['artist'], 'author': config['author'],
                          'album_art_file': str(cover), 'entries': selected}, indent=2))
        return
    if args.force:
        reset_output(output, [config_path,
                              resolve_path(config['input_csv'], config_path.parent),
                              cover, Path(__file__)])
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    downloaded = updated = 0
    failures = []
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {executor.submit(download_entry, entry, output, cover, config, args.overwrite): entry for entry in selected}
        for future in as_completed(futures):
            try:
                result = future.result()
                if result == 'downloaded':
                    downloaded += 1
                elif result == 'updated':
                    updated += 1
            except Exception as exc:
                failures.append(futures[future]['track'])
                print(str(exc))
    elapsed = time.monotonic() - started
    print(f'Downloaded {downloaded} files in {elapsed:.1f} seconds. '
          f'Metadata updated: {updated}. Failed: {len(failures)}.')
    if failures:
        raise SystemExit(f'Failed tracks: {sorted(failures)}')


if __name__ == '__main__':
    main()
