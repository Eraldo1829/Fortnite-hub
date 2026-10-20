// Public publisher feeds are secondary reporting, never a substitute for X verification.
export const leakSources=[
 {id:'hypex',name:'HYPEX on X',publisher:'@HYPEX · X',url:'https://x.com/HYPEX',kind:'community'},
 {id:'fortnite-leak-reports',name:'Fortnite leak reports',publisher:'Dexerto / GamesRadar+',url:'https://www.dexerto.com/fortnite/',kind:'secondary'}];
const feeds=[{url:'https://www.dexerto.com/fortnite/feed/',host:'www.dexerto.com',publisher:'Dexerto'},{url:'https://www.gamesradar.com/feeds/tag/fortnite/',host:'www.gamesradar.com',publisher:'GamesRadar+'}];
const decode=s=>s.replace(/<!\[CDATA\[|\]\]>/g,'').replace(/<[^>]*>/g,' ').replace(/&#x([0-9a-f]+);/gi,(_,n)=>String.fromCodePoint(parseInt(n,16))).replace(/&#([0-9]+);/g,(_,n)=>String.fromCodePoint(Number(n))).replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&apos;|&#39;/g,"'").replace(/\s+/g,' ').trim();
const tag=(s,n)=>(s.match(new RegExp('<'+n+'(?:\\s[^>]*)?>([\\s\\S]*?)</'+n+'>','i'))||[])[1]||'';
export function parseReports(xml,feed,now=Date.now()){
 const items=[];for(const m of xml.matchAll(/<item(?:\s[^>]*)?>([\s\S]*?)<\/item>/gi)){
  const raw=m[1],title=decode(tag(raw,'title')),url=decode(tag(raw,'link')),date=Date.parse(decode(tag(raw,'pubDate')));
  if(!/fortnite/i.test(title)||!/(leak|rumou?r|datamin)/i.test(title)||!Number.isFinite(date)||date>now||now-date>90*86400000)continue;
  try{const u=new URL(url);if(u.protocol!=='https:'||u.hostname!==feed.host)continue}catch{continue}
  items.push({title,url,game:'Fortnite',gameId:'fortnite',publisher:feed.publisher,publishedAt:new Date(date).toISOString(),kind:'leak',verification:'secondary',sourceHandle:null,originalPostUrl:null});
 }return items;
}
async function get(url,headers={}){const r=await fetch(url,{signal:AbortSignal.timeout(12000),headers:{'User-Agent':'GamePulse/1.1 (+gaming-news-index)',...headers}});if(!r.ok)throw Error('HTTP '+r.status);return r}
let hypexId=null;
async function hypex(){const source=leakSources[0];if(!process.env.X_BEARER_TOKEN)return {source,status:'not_configured',items:[],checkedAt:new Date().toISOString()};
 try{const headers={Authorization:'Bearer '+process.env.X_BEARER_TOKEN};if(!hypexId){const j=await(await get('https://api.x.com/2/users/by/username/HYPEX',headers)).json();hypexId=j.data?.id;if(!/^[0-9]+$/.test(hypexId||''))throw Error('No user')}
 const url=new URL('https://api.x.com/2/users/'+hypexId+'/tweets');url.searchParams.set('max_results','30');url.searchParams.set('exclude','retweets,replies');url.searchParams.set('tweet.fields','created_at');const j=await(await get(url,headers)).json();
 const items=(j.data||[]).filter(p=>/fortnite|fortnitemares|fncs|uefn/i.test(p.text)&&!/use (?:my )?code|giveaway/i.test(p.text)).map(p=>({title:decode(p.text.replace(/https:\/\/t\.co\/\S+/g,'')).slice(0,200),url:'https://x.com/HYPEX/status/'+p.id,originalPostUrl:'https://x.com/HYPEX/status/'+p.id,game:'Fortnite',gameId:'fortnite',publisher:'@HYPEX on X',sourceHandle:'@HYPEX',publishedAt:p.created_at||null,kind:/leak|rumou?r|datamin|upcoming/i.test(p.text)?'leak':'community',verification:'original_post'}));return {source,status:items.length?'ok':'empty',items,checkedAt:new Date().toISOString()};
 }catch{return {source,status:'unavailable',items:[],checkedAt:new Date().toISOString()}}
}
async function reports(){const source=leakSources[1];let success=0;const collected=await Promise.all(feeds.map(async feed=>{try{const items=parseReports(await(await get(feed.url)).text(),feed);success++;return await Promise.all(items.slice(0,6).map(async item=>{try{const html=await(await get(item.url)).text();const original=html.match(/https?:\/\/(?:x\.com|twitter\.com)\/HYPEX\/status\/[0-9]+/i)?.[0];if(original){item.originalPostUrl=original.replace('twitter.com','x.com');item.sourceHandle='@HYPEX'}}catch{}return item}))}catch{return []}}));
 const seen=new Set();const items=collected.flat().filter(item=>{const key=item.originalPostUrl||item.title.toLowerCase().replace(/[^a-z0-9]/g,'');if(seen.has(key))return false;seen.add(key);return true});return {source,status:success?(items.length?'ok':'empty'):'unavailable',items,checkedAt:new Date().toISOString()};}
export async function collectLeaks(){return Promise.all([hypex(),reports()])}
