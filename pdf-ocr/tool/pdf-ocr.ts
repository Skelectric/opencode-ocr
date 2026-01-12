import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Extract text from PDF files using DeepSeek-OCR. Processes entire PDFs and returns markdown or plain text output. Use this when you need to transcribe PDF documents for analysis or processing.",
  args: {
    pdf_path: tool.schema.string().describe("Absolute path to PDF file"),
    output_format: tool.schema.string().describe("Output format: 'markdown' or 'text' (defaults to 'markdown')")
  },
  async execute(args) {
    const result = await Bun.$`uv run --directory ~/.config/opencode/tool --env-file ~/.config/opencode/tool/.env pdf_ocr_backend.py ${args.pdf_path} ${args.output_format || 'markdown'}`.text()
    return result.trim()
  }
})
