import { tool } from "@opencode-ai/plugin"
import { resolve } from "path"

export default tool({
  description: "Extract text from PDF files using DeepSeek-OCR. Processes entire PDFs or specific pages and returns markdown or plain text output. Use this when you need to transcribe PDF documents for analysis or processing.",
  args: {
    pdf_path: tool.schema.string().describe("Path to PDF file (absolute or relative to current directory)"),
    output_format: tool.schema.string().describe("Output format: 'markdown' or 'text' (defaults to 'markdown')"),
    page: tool.schema.string().optional().describe("Page(s) to OCR: single page ('5'), range ('1-5'), multiple ('1,3,5'), or mixed ('1-3,5,7-9'). If omitted, all pages are processed.")
  },
  async execute(args) {
    // Convert relative paths to absolute paths
    const absolutePath = resolve(args.pdf_path)
    const result = args.page 
      ? await Bun.$`uv run --directory ~/.config/opencode/tool --env-file ~/.config/opencode/tool/.env pdf_ocr_backend.py ${absolutePath} ${args.output_format || 'markdown'} --page ${args.page}`.text()
      : await Bun.$`uv run --directory ~/.config/opencode/tool --env-file ~/.config/opencode/tool/.env pdf_ocr_backend.py ${absolutePath} ${args.output_format || 'markdown'}`.text()
    return result.trim()
  }
})
