import os
import sys


def pipe_input(prompt_input):
    if isinstance(prompt_input, str):
        prompt_input = prompt_input.encode("utf-8")
    r, w = os.pipe()
    os.dup2(r, sys.stdin.fileno())
    os.write(w, prompt_input)
