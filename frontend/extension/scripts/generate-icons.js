/**
 * generate-icons.js
 *
 * Generates minimal PNG placeholder icons for the Chrome extension.
 * Run with: node scripts/generate-icons.js
 */

const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const SIZES = [16, 48, 128];
const OUT_DIR = path.join(__dirname, "..", "icons");

fs.mkdirSync(OUT_DIR, { recursive: true });

// CRC-32 lookup table
const CRC_TABLE = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  let c = i;
  for (let k = 0; k < 8; k++) {
    c = (c & 1) ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  }
  CRC_TABLE[i] = c;
}

function crc32(buf) {
  let c = 0xffffffff;
  for (const byte of buf) {
    c = CRC_TABLE[(c ^ byte) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

function makeChunk(type, data) {
  const typeBytes = Buffer.from(type, "ascii");
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length, 0);
  const crcBuf = Buffer.concat([typeBytes, data]);
  const crcVal = crc32(crcBuf);
  const crcBytes = Buffer.alloc(4);
  crcBytes.writeUInt32BE(crcVal >>> 0, 0);
  return Buffer.concat([len, typeBytes, data, crcBytes]);
}

function makeSolidPng(width, height, r, g, b) {
  const rowSize = width * 4;
  const raw = Buffer.alloc(height * (1 + rowSize));

  for (let y = 0; y < height; y++) {
    const rowStart = y * (1 + rowSize);
    raw[rowStart] = 0; // Filter type: 0 (None)
    for (let x = 0; x < width; x++) {
      const base = rowStart + 1 + x * 4;
      raw[base] = r;
      raw[base + 1] = g;
      raw[base + 2] = b;
      raw[base + 3] = 255; // Alpha
    }
  }

  const compressed = zlib.deflateSync(raw);

  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8; // Bit depth: 8
  ihdrData[9] = 6; // Color type: RGBA
  ihdrData[10] = 0;
  ihdrData[11] = 0;
  ihdrData[12] = 0;

  const ihdr = makeChunk("IHDR", ihdrData);
  const idat = makeChunk("IDAT", compressed);
  const iend = makeChunk("IEND", Buffer.alloc(0));

  return Buffer.concat([sig, ihdr, idat, iend]);
}

for (const size of SIZES) {
  const png = makeSolidPng(size, size, 13, 35, 64); // #0d2340 navy
  const outPath = path.join(OUT_DIR, `icon${size}.png`);
  fs.writeFileSync(outPath, png);
  console.log(`Created ${outPath} (${size}x${size})`);
}
