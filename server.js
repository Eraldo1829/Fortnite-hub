import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {news,page} from './content.js';
const file=process.env.DATA_FILE||'/tmp/gamepulse-news.json';
let snapshot={checkedAt:null,results:[]},busy=false;
try{snapshot=JSON.parse(await fs.readFile(file,'utf8'));}catch{}
async function refresh(){if(busy)return;busy=true;try{const incoming=await news();incoming.results=incoming.results.map(r=>{const old=snapshot.results.find(o=>o.source.id===r.source.id);const merged=new Map((old?.items||[]).map(i=>[i.url,i]));for(const item of r.items)merged.set(item.url,item);return {...r,items:[...merged.values()].slice(-500)}});snapshot=incoming;await fs.mkdir(path.dirname(file),{recursive:true});await fs.writeFile(file+'.tmp',JSON.stringify(snapshot));await fs.rename(file+'.tmp',file);console.log('Collection complete',incoming.results.map(r=>r.source.id+':'+r.status+':'+r.items.length).join(' '));}catch(e){console.error('Collection failed:',e.message)}finally{busy=false}}
const server=http.createServer((req,res)=>{const u=new URL(req.url,'http://localhost');res.setHeader('X-Content-Type-Options','nosniff');if(u.pathname==='/healthz'){res.writeHead(200,{'Content-Type':'application/json'});return res.end(JSON.stringify({status:'ok',lastCollection:snapshot.checkedAt}));}if(u.pathname==='/api/news'){res.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'public, max-age=60'});return res.end(JSON.stringify(snapshot));}if(u.pathname!=='/'){res.writeHead(404);return res.end('Not found')}res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(page)});
server.listen(Number(process.env.PORT||3000),'0.0.0.0',()=>console.log('GamePulse listening'));
refresh();const interval=setInterval(refresh,15*60*1000);interval.unref();
process.on('SIGTERM',()=>{clearInterval(interval);server.close(()=>process.exit(0));});
