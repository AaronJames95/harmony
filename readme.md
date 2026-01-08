OK wow. Yes this is Harmony. The idea is that it is an alternative operating system that will run on top of whatever you're running. It is A voice controlled Applied AI interface.

## Current Target
Implement AI video and audio to text functionality

## Sleep Mode vLLM
You absolutely can just press Ctrl+C. In a standard Linux terminal, that sends a SIGINT signal, which usually tells vLLM to shut down gracefully and release the VRAM.

However, there are three reasons why the "unload script" is better than just hitting Ctrl+C:
1. The "Zombie" Process Problem

vLLM often spawns multiple sub-processes (especially if you use tensor-parallelism or specific GPU kernels). Sometimes, pressing Ctrl+C kills the main "window" but leaves a "zombie" process running in the background.

    The Result: Your terminal looks empty, but nvidia-smi shows 22GB/24GB used. You can't start a new model because the "ghost" of the old one is still squatting on the VRAM.

    The Script Fix: Using pkill -f vllm ensures every hidden sub-process is wiped out.

2. Why "Sleep" instead of "Kill"?

You asked: Why sleep when I could just kill?

    Startup Speed: Loading a 32B model into a 3090 takes about 45–90 seconds because it has to read 20GB+ from your disk and initialize the CUDA kernels.

    Sleep Mode: Takes about 1–2 seconds to "Wake Up" because the infrastructure (the CUDA graph and memory pool) is already initialized in your RAM.

    The Verdict: If you are switching models every 10 minutes, Sleep is a godsend. If you’re done for the day, Kill is better.

## QC
* If you don't if you need to create a new environment then you can do that using Mamba and the environment yaml file provided in the server directory.
* /home/aharon/miniforge3/envs/muscular_env/bin/python
* start tailscale with `sudo tailscale web`
* Note: Remote access requires sudo systemctl edit ollama.service with OLLAMA_HOST=0.0.0.0

## Macros
