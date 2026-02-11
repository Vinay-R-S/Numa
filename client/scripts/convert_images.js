const sharp = require("sharp");
const fs = require("fs");
const path = require("path");

const directoryPath = path.join(__dirname, "../assets/Images");

// Ensure the directory exists
if (!fs.existsSync(directoryPath)) {
  console.error(`Directory not found: ${directoryPath}`);
  process.exit(1);
}

fs.readdir(directoryPath, (err, files) => {
  if (err) {
    return console.error("Unable to scan directory: " + err);
  }

  files.forEach((file) => {
    const filePath = path.join(directoryPath, file);
    const fileExt = path.extname(file).toLowerCase();

    // Filter for image files
    if (
      [".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".avif"].includes(
        fileExt,
      )
    ) {
      const outputFileName = path.basename(file, fileExt) + ".webp";
      const outputFilePath = path.join(directoryPath, outputFileName);

      // Handle case where input and output paths are the same (e.g. input is already .webp)
      let sharpInstance = sharp(filePath).resize(512, 512).toFormat("webp");

      if (filePath === outputFilePath) {
        // If the file is already webp, we need to process it to a buffer first or temp file
        // to avoid reading and writing to the same file simultaneously
        sharpInstance
          .toBuffer()
          .then((data) => {
            fs.writeFile(outputFilePath, data, (err) => {
              if (err) console.error(`Error writing ${outputFileName}:`, err);
              else console.log(`Processed ${file} (Resized to 512x512)`);
            });
          })
          .catch((err) => {
            console.error(`Error processing ${file}:`, err);
          });
      } else {
        sharpInstance
          .toFile(outputFilePath)
          .then((info) => {
            console.log(`Converted ${file} to ${outputFileName} (512x512)`);
          })
          .catch((err) => {
            console.error(`Error processing ${file}:`, err);
          });
      }
    }
  });
});
