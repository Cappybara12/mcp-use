from hypertube.utils.RuntimeName import RuntimeName


class RuntimeNameHandler:

    @staticmethod
    def get_name(runtime_name):
        if isinstance(runtime_name, RuntimeName):
            if runtime_name == RuntimeName.clr:
                return "clr"
            elif runtime_name == RuntimeName.go:
                return "go"
            elif runtime_name == RuntimeName.jvm:
                return "jvm"
            elif runtime_name == RuntimeName.netcore:
                return "netcore"
            elif runtime_name == RuntimeName.perl:
                return "perl"
            elif runtime_name == RuntimeName.python:
                return "python"
            elif runtime_name == RuntimeName.ruby:
                return "ruby"
            elif runtime_name == RuntimeName.nodejs:
                return "nodejs"
            elif runtime_name == RuntimeName.php:
                return "php"
            elif runtime_name == RuntimeName.python27:
                return "python27"
        else:
            raise Exception("Invalid runtime name.")

    @staticmethod
    def get_runtime(name):
        if not name or name.strip() == "":
            raise ValueError("Runtime name cannot be null or whitespace.")
        name = name.strip().lower()
        if name == "clr":
            return RuntimeName.clr
        elif name == "go":
            return RuntimeName.go
        elif name == "jvm":
            return RuntimeName.jvm
        elif name == "netcore":
            return RuntimeName.netcore
        elif name == "perl":
            return RuntimeName.perl
        elif name == "python":
            return RuntimeName.python
        elif name == "ruby":
            return RuntimeName.ruby
        elif name == "nodejs":
            return RuntimeName.nodejs
        elif name == "php":
            return RuntimeName.php
        elif name == "python27":
            return RuntimeName.python27
        else:
            raise ValueError(f"{name} is not a supported runtime.")