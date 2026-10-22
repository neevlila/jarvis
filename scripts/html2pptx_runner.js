const pptxgen = require('pptxgenjs');
const html2pptx = require('./html2pptx.js');
const path = require('path');

async function run() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Usage: node html2pptx_runner.js <output_pptx_path> <html_file1> [html_file2] ...");
    process.exit(1);
  }

  const outputPath = args[0];
  const htmlFiles = args.slice(1);

  const pptx = new pptxgen();
  // Set layout to widescreen 16:9
  pptx.layout = 'LAYOUT_16x9';

  console.log(`Starting slide compilation for ${htmlFiles.length} slides...`);

  for (let i = 0; i < htmlFiles.length; i++) {
    const htmlFile = htmlFiles[i];
    const absPath = path.isAbsolute(htmlFile) ? htmlFile : path.resolve(process.cwd(), htmlFile);
    console.log(`[${i + 1}/${htmlFiles.length}] Compiling: ${absPath}`);
    try {
      await html2pptx(absPath, pptx);
    } catch (e) {
      console.error(`Error compiling slide ${i + 1} (${htmlFile}):`, e.message);
      process.exit(1);
    }
  }

  try {
    const finalPath = path.isAbsolute(outputPath) ? outputPath : path.resolve(process.cwd(), outputPath);
    console.log(`Writing presentation to: ${finalPath}`);
    await pptx.writeFile({ fileName: finalPath });
    console.log("Presentation generated successfully!");
  } catch (e) {
    console.error("Error writing PPTX file:", e.message);
    process.exit(1);
  }
}

run();
