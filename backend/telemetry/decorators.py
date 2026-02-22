"""
Decorators for easily adding telemetry to operations.

Provides simple decorators that can be applied to any function
to automatically track execution, measure performance, and enable replay.

Key Methods:
- `track_operation()`
- `decorator()`
- `track_tokens()`
- `wrapper()`
- `track_confidence()`
- `wrapper()`
"""
import functools
import json
import hashlib
import inspect
from typing import Callable, Any, Optional, Dict
from models.telemetry_models import OperationType
from telemetry.telemetry_service import get_telemetry_service


def track_operation(
    operation_type: OperationType,
    operation_name: Optional[str] = None,
    capture_inputs: bool = True,
    capture_outputs: bool = False
):
    """
    Decorator to automatically track an operation with telemetry.

    Usage:
        @track_operation(OperationType.INGESTION, "ingest_pdf")
        def ingest_pdf(filename: str, content: bytes):
            # Process PDF
            return result

    Args:
        operation_type: Type of operation (e.g., OperationType.INGESTION)
        operation_name: Name of the operation (defaults to function name)
        capture_inputs: Whether to store inputs for replay (default: True)
        capture_outputs: Whether to store outputs for comparison (default: False)
    """
    def decorator(func: Callable) -> Callable:
        # Determine operation name
        op_name = operation_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry_service()

            # Prepare metadata
            metadata: Dict[str, Any] = {
                "function": func.__name__,
                "module": func.__module__
            }

            # Capture inputs if requested
            input_data = None
            if capture_inputs:
                try:
                    # Get function signature
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    # Convert to serializable dict
                    input_dict = {}
                    for param_name, param_value in bound_args.arguments.items():
                        # Skip 'self' and 'cls'
                        if param_name in ('self', 'cls'):
                            continue

                        # Try to serialize the value
                        try:
                            json.dumps(param_value)
                            input_dict[param_name] = param_value
                        except (TypeError, ValueError):
                            # Can't serialize, store type instead
                            input_dict[param_name] = f"<{type(param_value).__name__}>"

                    input_data = input_dict
                    metadata['inputs'] = input_dict

                except Exception as e:
                    # If we can't capture inputs, log it but continue
                    metadata['input_capture_error'] = str(e)

            # Track the operation
            with telemetry.track_operation(
                operation_type=operation_type,
                operation_name=op_name,
                input_data=input_data,
                metadata=metadata
            ) as run_id:
                # Add run_id to kwargs if function accepts it
                sig = inspect.signature(func)
                if 'run_id' in sig.parameters:
                    kwargs['run_id'] = run_id

                # Execute the function
                result = func(*args, **kwargs)

                # Capture outputs if requested
                if capture_outputs:
                    try:
                        output_str = json.dumps(result, default=str)
                        output_hash = hashlib.sha256(output_str.encode()).hexdigest()
                        metadata['outputs'] = result
                        metadata['output_hash'] = output_hash
                    except Exception as e:
                        metadata['output_capture_error'] = str(e)

                return result

        return wrapper

    return decorator


def track_tokens(func: Callable) -> Callable:
    """
    Decorator to track token counts from a function's return value.

    Expects the function to return a dict with 'input_tokens' and/or
    'output_tokens' keys, or to accept run_id as a kwarg.

    Usage:
        @track_operation(OperationType.CHAT_GENERATION, "generate_response")
        @track_tokens
        def generate_response(prompt: str, run_id: str = None):
            result = llm.generate(prompt)
            return {
                "response": result,
                "input_tokens": 100,
                "output_tokens": 200
            }
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract run_id if present
        run_id = kwargs.get('run_id')

        # Execute function
        result = func(*args, **kwargs)

        # Record tokens if we have a run_id
        if run_id and isinstance(result, dict):
            telemetry = get_telemetry_service()
            input_tokens = result.get('input_tokens')
            output_tokens = result.get('output_tokens')

            if input_tokens or output_tokens:
                telemetry.record_tokens(
                    run_id=run_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )

        return result

    return wrapper


def track_confidence(func: Callable) -> Callable:
    """
    Decorator to track confidence scores from a function's return value.

    Expects the function to return a dict with 'confidence_score' and/or
    'contradiction_detected' keys.

    Usage:
        @track_operation(OperationType.RETRIEVAL, "retrieve_docs")
        @track_confidence
        def retrieve_docs(query: str, run_id: str = None):
            results = search(query)
            return {
                "results": results,
                "confidence_score": 0.85,
                "contradiction_detected": False
            }
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract run_id if present
        run_id = kwargs.get('run_id')

        # Execute function
        result = func(*args, **kwargs)

        # Record confidence if we have a run_id
        if run_id and isinstance(result, dict):
            telemetry = get_telemetry_service()
            confidence_score = result.get('confidence_score')
            contradiction_detected = result.get('contradiction_detected', False)

            if confidence_score is not None:
                telemetry.record_confidence(
                    run_id=run_id,
                    confidence_score=confidence_score,
                    contradiction_detected=contradiction_detected
                )

        return result

    return wrapper
