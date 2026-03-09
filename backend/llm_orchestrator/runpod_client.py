"""
RunPod LLM Client implementation for Serverless vLLM endpoints.
"""

import requests
import logging
import time
from typing import List, Dict, Any, Optional, Union
from .base_client import BaseLLMClient
from settings import settings

logger = logging.getLogger(__name__)

class RunPodLLMClient(BaseLLMClient):
    """
    Client for interacting with RunPod Serverless API.
    Handles the async 'run' endpoint and polls for results.
    """
    
    def __init__(self, api_key: str = None, endpoint_id: str = None):
        self.api_key = api_key or settings.RUNPOD_API_KEY
        self.endpoint_id = endpoint_id or settings.RUNPOD_ENDPOINT_ID
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        # RunPod Serverless usually takes a combined prompt or specific input structure
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}"
        
        # Following the user's example: {"input": {"prompt": "Your prompt"}}
        payload = {
            "input": {
                "prompt": full_prompt,
                "max_tokens": max_tokens or settings.MAX_NUM_PREDICT,
                "temperature": temperature if temperature is not None else 0.7,
            }
        }
        
        # Add any extra kwargs
        payload["input"].update(kwargs)

        try:
            # 1. Submit the job
            run_url = f"{self.base_url}/run"
            logger.info(f"Submitting RunPod job to: {run_url}")
            response = requests.post(run_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            
            job_data = response.json()
            job_id = job_data.get("id")
            
            if not job_id:
                raise ValueError("No job ID returned from RunPod")

            # 2. Poll for the result
            status_url = f"{self.base_url}/status/{job_id}"
            max_retries = 60 # 60 seconds timeout
            for i in range(max_retries):
                logger.debug(f"Polling RunPod job {job_id} (attempt {i+1})...")
                status_response = requests.get(status_url, headers=self.headers, timeout=10)
                status_response.raise_for_status()
                
                result = status_response.json()
                status = result.get("status")
                
                if status == "COMPLETED":
                    # Parse output based on user example: output[0]['choices'][0]['tokens'][0]
                    output = result.get("output")
                    if isinstance(output, list) and len(output) > 0:
                        choices = output[0].get("choices")
                        if choices and len(choices) > 0:
                            tokens = choices[0].get("tokens")
                            if tokens and len(tokens) > 0:
                                return tokens[0]
                    
                    # Fallback parsing if structure differs slightly
                    if isinstance(output, str):
                        return output
                    return str(output)
                
                elif status in ["FAILED", "CANCELLED"]:
                    error = result.get("error", "Unknown error")
                    raise RuntimeError(f"RunPod job {status}: {error}")
                
                # Wait before next poll
                time.sleep(1)
            
            raise TimeoutError(f"RunPod job {job_id} timed out")

        except Exception as e:
            logger.error(f"RunPod API request failed: {e}")
            raise

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        # For simplicity, convert chat messages to a single prompt
        # High-quality chat format for Qwen
        prompt = ""
        system_msg = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_msg = content
            elif role == "user":
                prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        
        prompt += "<|im_start|>assistant\n"
        
        return self.generate(
            prompt=prompt,
            system_prompt=system_msg,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

    def is_running(self) -> bool:
        """Check if the RunPod endpoint is reachable."""
        if not self.api_key or not self.endpoint_id:
            return False
        try:
            # Just check the status of a bogus job ID to verify headers/API connectivity
            url = f"{self.base_url}/health"
            requests.get(url, headers=self.headers, timeout=5)
            return True
        except Exception:
            return False

    def get_all_models(self) -> List[Dict[str, Any]]:
        """RunPod Serverless usually has one model per endpoint."""
        return [{"id": settings.RUNPOD_MODEL, "object": "model"}]

    def model_exists(self, model_name: str) -> bool:
        return model_name == settings.RUNPOD_MODEL or model_name == self.endpoint_id
