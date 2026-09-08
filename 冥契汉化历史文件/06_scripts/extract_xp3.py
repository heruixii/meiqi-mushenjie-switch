from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


def u64(data: bytes, offset: int) -> int:
    return struct.unpack_from('<Q', data, offset)[0]


def chunks(record: bytes):
    offset = 0
    while offset + 12 <= len(record):
        tag = record[offset:offset + 4]
        size = u64(record, offset + 4)
        start = offset + 12
        end = start + size
        if end > len(record):
            break
        yield tag, record[start:end], offset, end
        offset = end


def extract(archive: Path, output: Path) -> int:
    data = archive.read_bytes()
    if not data.startswith(b'XP3'):
        raise ValueError('not an XP3 archive')
    index_offset = u64(data, 11)
    index_flag = data[index_offset]
    compressed_size = u64(data, index_offset + 1)
    uncompressed_size = u64(data, index_offset + 9)
    index_data = data[index_offset + 17:index_offset + 17 + compressed_size]
    if index_flag & 1:
        index_data = zlib.decompress(index_data)
    if len(index_data) != uncompressed_size:
        raise ValueError('XP3 index size mismatch')

    output.mkdir(parents=True, exist_ok=True)
    pos = 0
    extracted = 0
    while pos + 12 <= len(index_data):
        if index_data[pos:pos + 4] != b'File':
            break
        record_size = u64(index_data, pos + 4)
        record_start = pos + 12
        record_end = record_start + record_size
        record = index_data[record_start:record_end]
        info = next((item for item in chunks(record) if item[0] == b'info'), None)
        segm = next((item for item in chunks(record) if item[0] == b'segm'), None)
        if info is None or segm is None:
            pos = record_end
            continue
        info_end = info[3]
        name_end = segm[2]
        info_data = info[1]
        flags = struct.unpack_from('<I', info_data, 0)[0]
        name_blob = info_data[22:]
        name = name_blob.decode('utf-16le').lstrip('\r\n').rstrip('\x00')
        segments = segm[1]
        if len(segments) == 0 or len(segments) % 28:
            pos = record_end
            continue
        segment_count = len(segments) // 28
        seg_pos = 0
        output_data = bytearray()
        for _ in range(segment_count):
            segment_flags = struct.unpack_from('<I', segments, seg_pos)[0]
            segment_offset = u64(segments, seg_pos + 4)
            segment_original = u64(segments, seg_pos + 12)
            segment_compressed = u64(segments, seg_pos + 20)
            seg_pos += 28
            payload = data[segment_offset:segment_offset + segment_compressed]
            if segment_flags & 1:
                payload = zlib.decompress(payload)
            if len(payload) != segment_original:
                raise ValueError(f'segment size mismatch: {name}')
            output_data.extend(payload)
        if not output_data:
            raise ValueError(f'file size mismatch: {name}')
        destination = output / Path(name.replace('\\', '/'))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(output_data)
        extracted += 1
        pos = record_end
    return extracted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(f'files_extracted={extract(args.archive, args.output)}')


if __name__ == '__main__':
    main()
