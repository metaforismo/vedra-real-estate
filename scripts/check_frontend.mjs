import {readdirSync, readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';
const root=dirname(dirname(fileURLToPath(import.meta.url)));
const files=readdirSync(join(root,'frontend/src')).filter(f=>f.endsWith('.js'));
for(const name of files){
  const result=spawnSync(process.execPath,['--input-type=module','--check'],{input:readFileSync(join(root,'frontend/src',name)),encoding:'utf8'});
  if(result.status!==0){process.stderr.write(result.stderr);process.exit(1);}
}
console.log(`${files.length} JavaScript modules: syntax OK`);
