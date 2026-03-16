# steam-item-certificate-tools

Small standalone repo that shows how to decode a Steam / CS2 `Item Certificate`.

## Files

- `decode_item_certificate.py`
  - The only script you need.
  - Takes one certificate string and prints:
    - the XOR key
    - the decoded certificate envelope
    - the protobuf payload hex
    - the resolved protobuf JSON
- `requirements.txt`
  - Python dependency list (`protobuf`)

## What The Decoder Does

An `Item Certificate` is not just a hash. It is an envelope around a normal `CEconItemPreviewDataBlock` protobuf payload.

The decoder:

1. Hex-decodes the certificate.
2. Uses the first byte as the XOR key.
3. XORs every byte with that key.
4. Drops the leading `00` byte.
5. Drops the trailing 4-byte trailer/checksum.
6. Returns the remaining bytes as the protobuf payload.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you do not want a virtual environment:

```bash
python3 -m pip install -r requirements.txt
```

## Quick Start

Resolve a certificate directly:

```bash
python3 decode_item_certificate.py 92826859045B28938A6E91B20991BA94A291AA016F546091D24895FAE5E29A90E5B003
```

Show the explanation from the CLI:

```bash
python3 decode_item_certificate.py --help
```

Normal output prints:

- the decoded envelope hex
- the embedded protobuf hex
- the resolved protobuf JSON

For wear values:

- `paintwear` is the raw protobuf uint32 value
- `paintwear_float` is that same value interpreted as an IEEE-754 float
