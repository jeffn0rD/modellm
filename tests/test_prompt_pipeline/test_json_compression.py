"""Round-trip tests for JSON compression module."""

import json
import pytest

from prompt_pipeline.compression.json_compression import (
    CompressionConfig,
    FilterConfig,
    FlattenConfig,
    KeyMappingConfig,
    TabularConfig,
    compress_json,
    decompress_json,
)


class TestJsonCompressionRoundTrip:
    """Test round-trip compression and decompression."""

    def test_simple_dict_with_identity_strategy(self):
        """Test simple dict with identity strategy - round-trip exact match."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }
        
        # Identity strategy (no compression)
        config = CompressionConfig(
            strategy="identity",
            key_mapping_config=KeyMappingConfig(enabled=False)
        )
        
        # Compress
        compressed = compress_json(data, config)
        
        # Decompress
        decompressed = decompress_json(compressed, config)
        
        # Verify round-trip
        assert decompressed == data, "Round-trip should preserve original data"

    def test_simple_dict_with_auto_abbrev(self):
        """Test simple dict with auto_abbrev strategy - round-trip exact match."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }
        
        # Auto abbrev strategy (field code mapping)
        config = CompressionConfig(
            strategy="auto_abbrev",
            key_mapping_config=KeyMappingConfig(enabled=True)
        )
        
        # Compress
        compressed = compress_json(data, config)
        
        # Decompress
        decompressed = decompress_json(compressed, config)
        
        # Verify round-trip
        assert decompressed == data, "Round-trip should preserve original data"

    def test_array_of_objects_non_tabular(self):
        """Test array of objects without tabular encoding - round-trip exact match."""
        data = {
            "items": [
                {"id": 1, "name": "item1", "value": 100},
                {"id": 2, "name": "item2", "value": 200},
                {"id": 3, "name": "item3", "value": 300},
            ]
        }
        
        config = CompressionConfig(
            strategy="test",
            key_mapping_config=KeyMappingConfig(enabled=True)
        )
        
        # Compress
        compressed = compress_json(data, config)
        
        # Decompress
        decompressed = decompress_json(compressed, config)
        
        # Verify round-trip
        assert decompressed == data, "Round-trip should preserve original data"
        assert "items" in decompressed
        assert len(decompressed["items"]) == 3

    def test_array_of_objects_tabular(self):
        """Test array of objects with tabular encoding - data is 2D list."""
        data = {
            "items": [
                {"id": 1, "name": "item1", "value": 100},
                {"id": 2, "name": "item2", "value": 200},
                {"id": 3, "name": "item3", "value": 300},
            ]
        }
        
        config = CompressionConfig(
            strategy="test",
            key_mapping_config=KeyMappingConfig(enabled=True),
            tabular_config=TabularConfig(
                enabled=True,
                tabular_fields=["items"]
            )
        )
        
        # Compress
        compressed = compress_json(data, config)
        
        # Decompress
        decompressed = decompress_json(compressed, config)
        
        # Verify round-trip
        assert decompressed == data, "Round-trip should preserve original data"
        assert "items" in decompressed
        assert len(decompressed["items"]) == 3
        assert decompressed["items"][0]["id"] == 1

    def test_filter_include_paths(self):
        """Test filter include_paths - filtered fields absent after decompress."""
        data = {
            "public": "public_value",
            "private": "private_value",
            "secret": "secret_value"
        }
        
        config = CompressionConfig(
            strategy="test",
            key_mapping_config=KeyMappingConfig(enabled=True),
            filter_config=FilterConfig(
                include_fields=["public", "private"]
            )
        )
        
        # Compress
        compressed = compress_json(data, config)
        
        # Decompress
        decompressed = decompress_json(compressed, config)
        
        # Verify only included fields are present
        assert "public" in decompressed
        assert "private" in decompressed
        assert "secret" not in decompressed

    def test_filter_exclude_paths(self):
        """Test filter exclude_paths - filtered fields absent after decompress."""
        data = {
            "public": "public_value",
            "private": "private_value",
            "secret": "secret_value"
        }
        
        config = CompressionConfig(
            strategy="test",
            key_mapping_config=KeyMappingConfig(enabled=True),
            filter_config=FilterConfig(
                exclude_fields=["secret"]
            )
        )
        
        # Compress
        compressed = compress_json(data, config)
        
        # Decompress
        decompressed = decompress_json(compressed, config)
        
        # Verify excluded field is not present
        assert "public" in decompressed
        assert "private" in decompressed
        assert "secret" not in decompressed

    def test_determinism(self):
        """Test determinism: same input -> same output twice."""
        data = {
            "user": {
                "name": "John Doe",
                "email": "john@example.com"
            },
            "items": [
                {"id": 1, "name": "item1"},
                {"id": 2, "name": "item2"}
            ]
        }
        
        config = CompressionConfig(
            strategy="test",
            key_mapping_config=KeyMappingConfig(enabled=True)
        )
        
        # Compress twice
        compressed1 = compress_json(data, config)
        compressed2 = compress_json(data, config)
        
        # Verify deterministic output
        assert compressed1 == compressed2, "Compressed output should be deterministic"
        
        # Decompress twice
        decompressed1 = decompress_json(compressed1, config)
        decompressed2 = decompress_json(compressed2, config)
        
        # Verify deterministic decompression
        assert decompressed1 == decompressed2, "Decompressed output should be deterministic"
