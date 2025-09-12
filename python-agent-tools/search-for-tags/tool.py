# This file is the implementation of custom agent tool search-for-tags
from dataiku.llm.agent_tools import BaseAgentTool


class CustomAgentTool(BaseAgentTool):
    def set_config(self, config, plugin_config):
        self.config = config

    def get_descriptor(self, tool):
        return {
            "description": "Hashes a string. Returns the SHA1 hash of the string.",
            "inputSchema" : {
                "$id": "https://example.com/agents/tools/hash/input",
                "title": "Input for the hashing tool",
                "type": "object",
                "properties" : {
                    "payload" : {
                        "type": "string",
                        "description": "The payload to hash"
                    }
                },
                "required": ["payload"]
            }
        }

    def invoke(self, input, trace):
        args = input["input"]
        payload = args["payload"]

        import hashlib
        sha1_hash = hashlib.sha1()
        sha1_hash.update(payload.encode('utf-8'))
        hashed = sha1_hash.hexdigest()

        return {
            "output": hashed,
            "sources":  [{
                "toolCallDescription": "Payload was hashed"
            }]
        }

    def load_sample_query(self, tool):
        return {"payload": "<Your payload to hash>"}
