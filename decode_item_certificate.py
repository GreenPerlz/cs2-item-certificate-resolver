#!/usr/bin/env python3
"""Explain and decode a Steam Item Certificate."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Take one CS2 Item Certificate, remove the certificate envelope, "
            "and print the embedded CEconItemPreviewDataBlock protobuf."
        ),
        epilog=(
            "How it works:\n"
            "  1. Hex-decode the Item Certificate.\n"
            "  2. Use the first byte as the XOR key.\n"
            "  3. XOR every byte with that key.\n"
            "  4. Remove the leading 00 byte.\n"
            "  5. Remove the trailing 4-byte trailer.\n"
            "  6. The remaining bytes are the protobuf payload."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "certificate",
        help="Upper/lower hex Item Certificate string.",
    )
    return parser.parse_args()


def sanitize_certificate(certificate: str) -> str:
    cleaned = "".join(certificate.split()).upper()
    if not cleaned:
        raise ValueError("certificate is empty")
    if len(cleaned) % 2 != 0:
        raise ValueError("certificate hex must have an even number of characters")
    try:
        bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ValueError("certificate contains non-hex characters") from exc
    return cleaned


def build_preview_message_class():
    """Build the public CEconItemPreviewDataBlock schema at runtime."""
    from google.protobuf import descriptor_pb2
    from google.protobuf import descriptor_pool
    from google.protobuf import message_factory

    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "econ_preview.proto"
    file_proto.syntax = "proto2"

    preview_msg = file_proto.message_type.add()
    preview_msg.name = "CEconItemPreviewDataBlock"

    sticker_msg = preview_msg.nested_type.add()
    sticker_msg.name = "Sticker"

    sticker_fields = [
        ("slot", 1, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32),
        ("sticker_id", 2, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32),
        ("wear", 3, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
        ("scale", 4, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
        ("rotation", 5, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
        ("tint_id", 6, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32),
        ("offset_x", 7, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
        ("offset_y", 8, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
        ("offset_z", 9, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
        ("pattern", 10, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32),
        ("highlight_reel", 11, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32),
        ("wrapped_sticker", 12, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32),
    ]

    for name, number, field_type in sticker_fields:
        field = sticker_msg.field.add()
        field.name = name
        field.number = number
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
        field.type = field_type

    preview_fields = [
        ("accountid", 1, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("itemid", 2, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64, None),
        ("defindex", 3, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("paintindex", 4, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("rarity", 5, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("quality", 6, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("paintwear", 7, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("paintseed", 8, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("killeaterscoretype", 9, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("killeatervalue", 10, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("customname", 11, descriptor_pb2.FieldDescriptorProto.TYPE_STRING, None),
        (
            "stickers",
            12,
            descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
            ".CEconItemPreviewDataBlock.Sticker",
        ),
        ("inventory", 13, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("origin", 14, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("questid", 15, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("dropreason", 16, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("musicindex", 17, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        ("entindex", 18, descriptor_pb2.FieldDescriptorProto.TYPE_INT32, None),
        ("petindex", 19, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        (
            "keychains",
            20,
            descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
            ".CEconItemPreviewDataBlock.Sticker",
        ),
        ("style", 21, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
        (
            "variations",
            22,
            descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
            ".CEconItemPreviewDataBlock.Sticker",
        ),
        ("upgrade_level", 23, descriptor_pb2.FieldDescriptorProto.TYPE_UINT32, None),
    ]

    repeated_fields = {"stickers", "keychains", "variations"}

    for name, number, field_type, type_name in preview_fields:
        field = preview_msg.field.add()
        field.name = name
        field.number = number
        field.label = (
            descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
            if name in repeated_fields
            else descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
        )
        field.type = field_type
        if type_name:
            field.type_name = type_name

    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_proto)
    descriptor = pool.FindMessageTypeByName("CEconItemPreviewDataBlock")
    return message_factory.GetMessageClass(descriptor)


def parse_preview_data_block(proto_bytes: bytes):
    message_class = build_preview_message_class()
    message = message_class()
    message.ParseFromString(proto_bytes)
    return message


def preview_to_dict(message) -> dict[str, Any]:
    from google.protobuf import json_format

    payload = json_format.MessageToDict(
        message,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=False,
    )
    if message.HasField("paintwear"):
        payload["paintwear_float"] = struct.unpack(
            "<f",
            struct.pack("<I", message.paintwear & 0xFFFFFFFF),
        )[0]
    return payload


def decode_certificate(certificate_hex: str) -> dict[str, Any]:
    certificate_bytes = bytes.fromhex(sanitize_certificate(certificate_hex))
    xor_key = certificate_bytes[0]
    decoded_envelope = bytes(byte ^ xor_key for byte in certificate_bytes)

    if len(decoded_envelope) < 6:
        raise ValueError("decoded certificate is too short to contain protobuf data")
    if decoded_envelope[0] != 0:
        raise ValueError(
            "decoded certificate envelope does not start with 0x00; XOR scheme changed?"
        )

    proto_bytes = decoded_envelope[1:-4]
    trailer = decoded_envelope[-4:]
    message = parse_preview_data_block(proto_bytes)

    return {
        "certificate_hex": certificate_bytes.hex().upper(),
        "xor_key_hex": f"{xor_key:02X}",
        "decoded_envelope_hex": decoded_envelope.hex().upper(),
        "protobuf_hex": proto_bytes.hex().upper(),
        "trailer_hex": trailer.hex().upper(),
        "resolved_protobuf": preview_to_dict(message),
    }


def print_text(result: dict[str, Any]) -> None:
    print(f"certificate_hex: {result['certificate_hex']}")
    print(f"xor_key_hex: {result['xor_key_hex']}")
    print(f"decoded_envelope_hex: {result['decoded_envelope_hex']}")
    print(f"protobuf_hex: {result['protobuf_hex']}")
    print(f"trailer_hex: {result['trailer_hex']}")
    print("resolved_protobuf_json:")
    print(json.dumps(result["resolved_protobuf"], indent=2, sort_keys=True))


def main() -> int:
    args = parse_args()

    try:
        result = decode_certificate(args.certificate)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
