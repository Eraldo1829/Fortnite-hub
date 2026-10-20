// Only public publisher feeds. No X API or X scraping.
export const leakSources=[
 {id:'leaks-dexerto',name:'Fortnite leaks · Dexerto',publisher:'Dexerto · leaks',url:'https://www.dexerto.com/fortnite/feed/',homepage:'https://www.dexerto.com/fortnite/',host:'www.dexerto.com',kind:'secondary'},
 {id:'leaks-gamesradar',name:'Fortnite leaks · GamesRadar+',publisher:'GamesRadar+ · leaks',url:'https://www.gamesradar.com/feeds/tag/fortnite/',homepage:'https://www.gamesradar.com/games/fortnite/',host:'www.gamesradar.com',kind:'secondary'},
 {id:'leaks-esportsgg',name:'Fortnite leaks · esports.gg',publisher:'esports.gg · leaks',url:'https://esports.gg/feed/',homepage:'https://esports.gg/games/fortnite/',host:'esports.gg',kind:'secondary'}];
const decode=s=>s.replace(/<!\[CDATA\[|\]\]>/g,'').replace(/<[^>]*>/g,' ').replace(/&#x([0-9a-f]+);/gi,(_,n)=>String.fromCodePoint(parseInt(n,16))).replace(/&#([0-9]+);/g,(_,n)=>String.fromCodePoint(Number(n))).replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&apos;|&#39;/g,"'").replace(/\s+/g,' ').trim();
const tag=(s,n)=>(s.match(new RegExp('<'+n+'(?:\\s[^>]*)?>([\\s\\S]*?)</'+n+'>','i'))||[])[1]||'';
export function parseReports(xml,feed,now=Date.now()){
 const items=[];for(const m of xml.matchAll(/<item(?:\s[^>]*)?>([\s\S]*?)<\/item>/gi)){
  const raw=m[1],title=decode(tag(raw,'title')),url=decode(tag(raw,'link')),date=Date.parse(decode(tag(raw,'pubDate')));
  if(!/fortnite/i.test(title)||!/(leak|rumou?r|datamin)/i.test(title)||!Number.isFinite(date)||date>now||now-date>90*86400000)continue;
  try{const u=new URL(url);if(u.protocol!=='https:'||u.hostname!==feed.host)continue}catch{continue}
  items.push({title,url,game:'Fortnite',gameId:'fortnite',publisher:feed.publisher,publishedAt:new Date(date).toISOString(),kind:/debunk|fake|false|hoax/i.test(title)?'debunked':/rumou?r/i.test(title)?'rumor':'leak',verification:'secondary',sourceHandle:null,originalPostUrl:null});
 }return items;
}
async function get(url,headers={}){const r=await fetch(url,{signal:AbortSignal.timeout(12000),headers:{'User-Agent':'GamePulse/1.1 (+gaming-news-index)',...headers}});if(!r.ok)throw Error('HTTP '+r.status);return r}
export async function collectLeaks(){return Promise.all(leakSources.map(async source=>{try{const xml=await(await get(source.url)).text();if(!/<rss|<feed[\s>]/i.test(xml))throw Error('Not a feed');const seen=new Set();const items=parseReports(xml,source).filter(i=>{const key=i.title.toLowerCase().replace(/[^a-z0-9]/g,'');if(seen.has(key))return false;seen.add(key);return true}).slice(0,30);return {source,status:items.length?'ok':'empty',items,checkedAt:new Date().toISOString()}}catch{return {source,status:'unavailable',items:[],checkedAt:new Date().toISOString()}}}))}
