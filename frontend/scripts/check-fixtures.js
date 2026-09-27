import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dataDir = path.join(__dirname, '..', 'public', 'data');

function checkDir(dir) {
  if (!fs.existsSync(dir)) return;
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const fullPath = path.join(dir, file);
    if (fs.statSync(fullPath).isDirectory()) {
      checkDir(fullPath);
    } else if (fullPath.endsWith('.json')) {
      try {
        const content = JSON.parse(fs.readFileSync(fullPath, 'utf-8'));
        if (content.meta && content.meta.fixture === true) {
          console.error(`\n❌ ERROR: Fixture data detected in ${fullPath}`);
          console.error(`Cannot build for demo/production with mock data.`);
          console.error(`Run 'make sync' on the backend first.\n`);
          process.exit(1);
        }
      } catch (e) {
        // Not a JSON or invalid JSON
      }
    }
  }
}

console.log('Checking for fixture data...');
checkDir(dataDir);
console.log('✅ No fixture data found.');
