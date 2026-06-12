#!/usr/bin/env python3
"""
Test script for Qwen Image Edit VAE decode fix.
Tests that VAE postprocessing handles 5D tensors correctly for editing models.
"""
import sys
import os
import torch
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import processing_vae, shared, devices
from unittest.mock import Mock, MagicMock
from PIL import Image


def test_vae_postprocess_qwen_image_edit():
    """Test VAE postprocessing with Qwen Image Edit tensor shapes."""
    print("\n=== Testing VAE postprocess for Qwen Image Edit ===\n")

    test_cases = [
        {
            "name": "QwenImageEditPipeline with 5D tensor [1,3,1,256,256]",
            "model_class": "QwenImageEditPipeline",
            "tensor_shape": (1, 3, 1, 256, 256),
            "expected_output_shape": (1, 3, 256, 256),
            "should_pass": True,
        },
        {
            "name": "QwenImageLayeredPipeline with 5D tensor [1,3,1,256,256]",
            "model_class": "QwenImageLayeredPipeline",
            "tensor_shape": (1, 3, 1, 256, 256),
            "expected_output_shape": (1, 3, 256, 256),
            "should_pass": True,
        },
        {
            "name": "QwenImagePipeline with 5D tensor [1,3,1,256,256]",
            "model_class": "QwenImagePipeline",
            "tensor_shape": (1, 3, 1, 256, 256),
            "expected_output_shape": (1, 3, 256, 256),
            "should_pass": True,
        },
        {
            "name": "QwenImageEditPipeline with 5D tensor [1,16,1,128,128]",
            "model_class": "QwenImageEditPipeline",
            "tensor_shape": (1, 16, 1, 128, 128),
            "expected_output_shape": (1, 3, 128, 128),
            "should_pass": True,
        },
    ]

    passed = 0
    failed = 0

    for test_case in test_cases:
        try:
            print(f"Testing: {test_case['name']}")

            # Create mock model
            model = Mock()
            model.__class__.__name__ = test_case["model_class"]
            model.image_processor = Mock()

            # Create tensor
            tensor = torch.randn(test_case["tensor_shape"])
            print(f"  Input tensor shape: {tensor.shape}")

            # Mock image_processor.postprocess to capture input shape
            captured_shape = None
            def mock_postprocess(t, output_type=None):
                nonlocal captured_shape
                captured_shape = t.shape
                # Return mock images
                return [Image.new('RGB', (t.shape[-1], t.shape[-2]))]

            model.image_processor.postprocess = mock_postprocess

            # Call vae_postprocess
            result = processing_vae.vae_postprocess(tensor, model, output_type='pil')

            # Verify result
            if captured_shape != test_case["expected_output_shape"]:
                print(f"  ❌ FAILED: Expected image_processor to receive {test_case['expected_output_shape']}, got {captured_shape}")
                failed += 1
            elif len(result) == 0:
                print(f"  ❌ FAILED: No images returned")
                failed += 1
            else:
                print(f"  ✓ PASSED: Output shape {captured_shape}, images={len(result)}")
                passed += 1

        except Exception as e:
            if test_case["should_pass"]:
                print(f"  ❌ FAILED with exception: {e}")
                failed += 1
            else:
                print(f"  ✓ PASSED (expected failure): {e}")
                passed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}\n")

    return failed == 0


def test_tensor_dimension_handling():
    """Test tensor dimension squeezing logic."""
    print("\n=== Testing tensor dimension handling ===\n")

    print("Test 1: QwenImageEdit with 5D [1,3,1,H,W]")
    tensor = torch.randn(1, 3, 1, 256, 256)
    model = Mock()
    model.__class__.__name__ = "QwenImageEditPipeline"
    model.image_processor = Mock()

    captured = []
    def capture(t, **kwargs):
        captured.append(t)
        return [Image.new('RGB', (t.shape[-1], t.shape[-2]))]

    model.image_processor.postprocess = capture
    processing_vae.vae_postprocess(tensor, model, output_type='pil')

    if len(captured) > 0:
        result_shape = captured[0].shape
        print(f"  Input: {tensor.shape} -> Output received: {result_shape}")
        if result_shape == (1, 3, 256, 256):
            print(f"  ✓ Correctly squeezed to 4D")
        else:
            print(f"  ❌ Unexpected shape")

    print("\nTest 2: QwenImageEdit with 5D [1,16,1,H,W] (should select first 3 channels)")
    tensor = torch.randn(1, 16, 1, 256, 256)
    model = Mock()
    model.__class__.__name__ = "QwenImageEditPipeline"
    model.image_processor = Mock()

    captured = []
    model.image_processor.postprocess = lambda t, **kwargs: (captured.append(t), [Image.new('RGB', (t.shape[-1], t.shape[-2]))])[1]
    processing_vae.vae_postprocess(tensor, model, output_type='pil')

    if len(captured) > 0:
        result_shape = captured[0].shape
        print(f"  Input: {tensor.shape} -> Output received: {result_shape}")
        if result_shape == (1, 3, 256, 256):
            print(f"  ✓ Correctly selected first 3 channels and squeezed depth")
        else:
            print(f"  ❌ Unexpected shape")

    print()


if __name__ == '__main__':
    # Initialize minimal shared state
    if not hasattr(shared, 'opts'):
        shared.opts = Mock()
        shared.opts.cuda_compile = ''
        shared.opts.sdnq_quantize_weights = ''
        shared.opts.openvino_disable_memory_cleanup = False
        shared.opts.diffusers_move_unet = False
        shared.opts.no_half_vae = False

    if not hasattr(shared, 'state'):
        shared.state = Mock()
        shared.state.interrupted = False
        shared.state.skipped = False

    if not hasattr(shared, 'mem_mon'):
        shared.mem_mon = Mock()
        shared.mem_mon.reset = Mock()
        shared.mem_mon.read = Mock(return_value={})

    # Run tests
    test_tensor_dimension_handling()
    success = test_vae_postprocess_qwen_image_edit()

    sys.exit(0 if success else 1)
