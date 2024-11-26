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

### Mac OS
To run OpenACI on macOS, we need xcode developer package.
```
xcode-select --install
```

Also install
```
pip install pyobjc-framework-ApplicationServices
```

## Contributing
Contributions to this experimental codebase are welcome. If you discover any issues, have suggestions, or would like to add new features, please open an issue or submit a pull request.

## License
This repository is licensed under the Apache 2.0. Please review the license file for more details.

## Disclaimer
The code provided in this repository is experimental in nature and may not be suitable for all use cases. The authors and contributors of this code are not responsible for any damages or losses incurred through the use of this code. Use it at your own risk.

Always exercise caution and follow best practices when using automation tools.

