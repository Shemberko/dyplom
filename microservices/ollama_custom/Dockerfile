FROM ollama/ollama:latest

ENV MODEL_NAME=llama3.2:1b

RUN nohup bash -c "ollama serve &" && sleep 5 && ollama pull $MODEL_NAME