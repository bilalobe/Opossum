# app/models/hybrid.py
class HybridModelBackend(ModelBackend):
    def __init__(self):
        self.gemini_backend = GeminiBackend()
        self.transformers_backend = TransformersBackend()

    async def generate_response(self, prompt, conversation_stage):
        if "image" in prompt:
            return await self.gemini_backend.generate_response(prompt, conversation_stage)
        return await self.transformers_backend.generate_response(prompt, conversation_stage)