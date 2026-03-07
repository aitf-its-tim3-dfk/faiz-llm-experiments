import httpx
import json
import asyncio
import subprocess
import time
import sys


async def test():
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Hit the actual server we just started
        content = "Ini berita hoaks! Uang Rp 100 ribu di dalamnya ada microchip yang bisa melacak kita!"
        print(f"Testing point /api/analyze (Multipart) with content:\n{content}\n")

        # Test with just text (multipart) and a custom config abstraction 
        # (e.g. fewer fact-check loops for a faster ablation test)
        custom_config = {
            "fact_checker_max_loops": 1, 
            "classifier_model_name": "qwen/qwen3.5-35b-a3b"
        }
        
        async with client.stream(
            "POST",
            "http://127.0.0.1:8000/api/analyze",
            data={
                "content": content,
                "config": json.dumps(custom_config)
            },
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        payload = json.loads(line[6:])
                        if payload["type"] == "progress":
                            stage = payload["data"].get("stage", "??")
                            print(f"[PROGRESS] [{stage}] {payload['data']['message']}")
                        elif payload["type"] == "result":
                            print("\n[FINAL RESULT]")
                            print(json.dumps(payload["data"], indent=2, ensure_ascii=False))
                        elif payload["type"] == "error":
                            print("\n[ERROR]")
                            print(payload["data"])
                    except json.JSONDecodeError:
                        pass


if __name__ == "__main__":
    print("Starting Sanic server in the background...")
    # Start the server using the active Python environment
    server_process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd="c:/Users/kek/projects/faiz-llm-experiments/app"
    )
    
    try:
        print("Waiting for server to become ready...")
        # Poll the server until it's ready
        max_retries = 30
        for i in range(max_retries):
            try:
                # Just hit the root endpoint to check if it's up
                httpx.get("http://127.0.0.1:8000/", timeout=1.0)
                print("Server is up!")
                break
            except httpx.RequestError:
                time.sleep(2)
        else:
            print("Server failed to start within the timeout.")
            server_process.terminate()
            exit(1)

        print("\n--- Running Tests ---")
        asyncio.run(test())
    finally:
        print("\nStopping Sanic server...")
        server_process.terminate()
        server_process.wait()

