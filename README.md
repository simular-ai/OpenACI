# OpenACI: Open Source Agent Computer Interface

tl;dr: OpenACI is an interfact that allows computers to control itself and perform tasks autonomously according to natural langauge instructions.

## Introduction
Imagine a world where humans and computers interact seamlessly, effortlessly, and intuitively. Welcome to OpenACI, the revolutionary Open Source Agent Computer Interface that’s redefining the boundaries of human-computer interaction. Inspired by the idea that technology should serve humans, not the other way around, OpenACI is a pioneering platform that enables users to interact with computers in a more natural, conversational way. By harnessing the power of artificial intelligence, machine learning, and natural language processing, OpenACI is poised to transform the way we live, work, and communicate in the digital age.

## Warning
Using automation tools can be potentially dangerous if not used responsibly. Please be aware of the following risks and guidelines before attempting to use this code:

1. **Unauthorized access:** Automating tasks can involve interacting with sensitive information or systems. Ensure that you have proper authorization and permissions before using this code on any platform or application.
2. **Data loss or corruption:** Incorrect usage of automation tools can result in data loss or corruption. Carefully review and test the code before running it on any important files or data.
3. **Unintended consequences:** Automating tasks can sometimes lead to unintended consequences. Always verify the behavior of the code and ensure that it performs the intended actions.
4. **System instability:** Depending on the complexity of the automated tasks, there is a risk of causing system instability or crashes. This can lead to loss of work or damage to the system. Use this code in controlled environments and be prepared to handle any unforeseen issues.
5. **Legal implications:** Some actions performed through automation may violate the terms of service or laws of certain platforms or jurisdictions. Ensure that you comply with all applicable rules and regulations before running this code.

## Initializing OCR and Retrieval From Web 

To use RAG and OCR complete the below steps before running the run.py script

### Using RAG with Perplexica API

#### Getting Started with Docker

1. Ensure Docker is installed and running on your system.
2. Clone the Perplexica repository:

   ```bash
   git clone https://github.com/ItzCrazyKns/Perplexica.git
   ```

3. After cloning, navigate to the directory containing the project files.

4. Rename the `sample.config.toml` file to `config.toml`. For Docker setups, you need only fill in the following fields:

   - `OPENAI`: Your OpenAI API key. **You only need to fill this if you wish to use OpenAI's models**.
   - `OLLAMA`: Your Ollama API URL. You should enter it as `http://host.docker.internal:PORT_NUMBER`. If you installed Ollama on port 11434, use `http://host.docker.internal:11434`. For other ports, adjust accordingly. **You need to fill this if you wish to use Ollama's models instead of OpenAI's**.
   - `GROQ`: Your Groq API key. **You only need to fill this if you wish to use Groq's hosted models**.
   - `ANTHROPIC`: Your Anthropic API key. **You only need to fill this if you wish to use Anthropic models**.

     **Note**: You can change these after starting Perplexica from the settings dialog.

   - `SIMILARITY_MEASURE`: The similarity measure to use (This is filled by default; you can leave it as is if you are unsure about it.)

5. Ensure you are in the directory containing the `docker-compose.yaml` file and execute:

   ```bash
   docker compose up -d
   ```

6. Wait a few minutes for the setup to complete. You can access Perplexica at http://localhost:3000 in your web browser.

**Note**: After the containers are built, you can start Perplexica directly from Docker without having to open a terminal.


### Using OCR 

Install fastapi and then run the ocr_server.py file code to use OCR-based bounding boxes. 

```
pip install fastapi
cd ui_agent
python ocr_server.py
```

In the terminal window where you will run the run.py file type the following lines:

```
export OCR_SERVER_ADDRESS=http://localhost:8000/ocr/
```

You can change the server address based on whatever address you use in the ui_agent/ocr_server.py file 

## Usage
To use this experimental code, follow the steps below:

1. Clone the repository to your local machine and navigate into the cloned repo: 
```shell
git clone https://github.com/simular-ai/OpenACI
cd OpenACI
```
2. Install the required dependencies: 
```shell
pip install -r requirements.txt
```
3. Export your OpenAI API key:
```shell
export OPENAI_API_KEY=<openai-api-key>
```
4. Install the openaci package in editable mode:
```shell
pip install -e .
``` 
5. Run the code using
```shell
python openaci/cli_app.py
```
6. Write an instruction for the agent as query. You can interrupt the agent at any time with a keyboard interrupt (Ctrl+C) in the terminal to run it.

Please remember to review and modify the code according to your specific use case and requirements. It is highly recommended to thoroughly test the code in a controlled environment before using it in any production or critical systems.

## Contributing
Contributions to this experimental codebase are welcome. If you discover any issues, have suggestions, or would like to add new features, please open an issue or submit a pull request.

## License
This repository is licensed under the Apache 2.0. Please review the license file for more details.

## Disclaimer
The code provided in this repository is experimental in nature and may not be suitable for all use cases. The authors and contributors of this code are not responsible for any damages or losses incurred through the use of this code. Use it at your own risk.

Always exercise caution and follow best practices when using automation tools.

