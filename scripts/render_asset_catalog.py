#!/usr/bin/env python3
"""Verify the downloaded asset bytes and build an offline contact sheet and ZIP."""
import hashlib
import html
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets/endfield-wiki"
GROUPS = {"backgrounds": "背景与纹理", "icons": "功能与菜单图标", "branding": "标志参考"}


def main():
    manifest = json.loads((ASSETS / "manifest.json").read_text())
    assets = manifest["assets"]
    cards = []
    for asset in assets:
        path = (ASSETS / asset["path"]).resolve()
        if not path.is_relative_to(ASSETS.resolve()):
            raise ValueError("Asset escapes catalog directory")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != asset["sha256"]:
            raise ValueError(f"Asset changed: {asset['path']}")
        escape = html.escape
        search = escape(" ".join([asset["title"], asset["wiki_filename"], asset["suggested_use"]]).lower(), quote=True)
        meta = f"{asset['width']} × {asset['height']} · {path.suffix[1:].upper()}"
        if asset["has_alpha_channel"]:
            meta += " · 透明通道"
        cards.append(f'''<article class="asset {asset['category']}" data-category="{asset['category']}" data-search="{search}">
  <a class="preview" href="{escape(asset['path'], quote=True)}" target="_blank" rel="noopener" aria-label="打开 {escape(asset['title'], quote=True)} 原尺寸素材"><img src="{escape(asset['path'], quote=True)}" alt="{escape(asset['title'], quote=True)}" width="{asset['width']}" height="{asset['height']}"></a>
  <div class="details"><span class="group">{GROUPS[asset['category']]}</span><h2>{escape(asset['title'])}</h2><p class="filename">{escape(asset['wiki_filename'])}</p><p class="meta">{meta}</p><p class="usage">{escape(asset['suggested_use'])}</p>
  <div class="links"><a href="{escape(asset['path'], quote=True)}" download>下载素材</a><a href="{escape(asset['source_page'], quote=True)}" target="_blank" rel="noopener">Wiki 文件页 ↗</a></div></div>
</article>''')
    counts = {group: sum(asset["category"] == group for asset in assets) for group in GROUPS}
    total_size = sum(asset["bytes"] for asset in assets) / (1024 * 1024)
    controls = ''.join(f'<button type="button" data-filter="{group}" aria-pressed="false">{name} <span>{counts[group]}</span></button>' for group, name in GROUPS.items())
    page = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Endfield Wiki 素材库 · Harness 皮肤准备</title>
<style>
:root{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;color:#e8eaed;background:#141619;font-synthesis:none}*{box-sizing:border-box}body{margin:0}a{color:inherit}button,input{font:inherit}header,main,footer{max-width:1380px;margin:auto;padding:32px}header{padding-top:44px;padding-bottom:20px}.eyebrow{font-size:12px;color:#a9afb9;letter-spacing:.12em}h1{font-size:32px;line-height:1.3;margin:10px 0 14px}.intro{color:#b9bec7;line-height:1.8;font-size:14px;margin:0;max-width:780px}.summary{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}.summary span{font-size:12px;padding:7px 10px;border:1px solid #353941;border-radius:4px}.toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:space-between;margin-bottom:20px}.filters,.surface{display:flex;gap:6px;flex-wrap:wrap}button{cursor:pointer;border:1px solid #393e47;color:#bcc2cc;background:#1d2026;border-radius:5px;padding:9px 12px;font-size:13px}button[aria-pressed=true]{background:#edf0f5;color:#20252c;border-color:#edf0f5}button span{opacity:.65;margin-left:4px}button:hover{border-color:#a2aab8}button:focus-visible,a:focus-visible,input:focus-visible{outline:2px solid #a9c9ff;outline-offset:3px}.search{display:flex;gap:8px;align-items:center;font-size:13px;color:#bfc5cf}.search input{width:240px;max-width:70vw;padding:9px 11px;background:#1d2026;color:#fff;border:1px solid #393e47;border-radius:5px}.statusline{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:18px;color:#a9afb9;font-size:12px}.surface{align-items:center}.surface button{font-size:12px;padding:6px 9px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.asset{border:1px solid #333841;border-radius:7px;overflow:hidden;min-width:0;background:#1b1e23}.asset.backgrounds{grid-column:span 2}.asset[hidden]{display:none}.preview{height:164px;display:flex;align-items:center;justify-content:center;background:#262a31;border-bottom:1px solid #333841;padding:24px}.backgrounds .preview{height:230px;padding:0}.branding .preview{height:190px;padding:28px}.preview img{max-width:100%;max-height:100%;object-fit:contain;width:auto;height:auto}.icons .preview img{max-width:100px;max-height:100px}.backgrounds .preview img{width:100%;height:100%;object-fit:contain}body[data-surface=light] .preview{background:#eceef0}body[data-surface=checker] .preview{background-color:#a5a8ae;background-image:linear-gradient(45deg,#d0d3d8 25%,transparent 25%),linear-gradient(-45deg,#d0d3d8 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#d0d3d8 75%),linear-gradient(-45deg,transparent 75%,#d0d3d8 75%);background-size:20px 20px;background-position:0 0,0 10px,10px -10px,-10px 0}.details{padding:16px}.group{font-size:10px;color:#9ba4b3;letter-spacing:.06em}h2{font-size:16px;font-weight:600;margin:8px 0}.filename{font-size:11px;color:#aab1be;overflow-wrap:anywhere;margin:0}.meta{font-size:11px;color:#8f99aa;margin:8px 0}.usage{font-size:12px;line-height:1.6;color:#c2c8d1;min-height:20px;margin:10px 0 15px}.links{display:flex;gap:16px;font-size:12px}.links a{text-decoration:none;border-bottom:1px solid #555e6d;padding-bottom:3px}.empty{color:#bfc5cf;padding:50px 0}footer{color:#8e98a8;font-size:12px;line-height:1.9;padding-top:8px;padding-bottom:40px}footer p{max-width:900px}footer a{color:#b8c5db}@media(max-width:900px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}.asset.backgrounds{grid-column:span 3}}@media(max-width:650px){header,main,footer{padding-left:18px;padding-right:18px}h1{font-size:26px}.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.asset.backgrounds{grid-column:span 2}.preview{height:130px}.details{padding:12px}.links{gap:10px;flex-wrap:wrap}.search input{width:240px}.backgrounds .preview{height:190px}}
</style></head><body data-surface="dark">
<header><div class="eyebrow">HARNESS / ASSET REFERENCE</div><h1>Endfield Wiki 素材库</h1><p class="intro">用于 DeepSeek Harness 皮肤的素材选型。点击图片可查看完整尺寸；浅底、深底和棋盘切换方便检查透明素材。具体皮肤风格尚未确定。</p>
<div class="summary"><span>__COUNT__ 项素材</span><span>__SIZE__ MB</span><span>来源：Endfield Talos Wiki</span><span>收集于 2026-10-31</span></div></header>
<main><div class="toolbar"><div class="filters" aria-label="素材分类"><button type="button" data-filter="all" aria-pressed="true">全部 <span>__COUNT__</span></button>__FILTERS__</div><label class="search">搜索<input type="search" placeholder="名称、用途或文件名" aria-label="搜索素材"></label></div>
<div class="statusline"><span id="result-count" aria-live="polite">显示 __COUNT__ / __COUNT__ 项</span><div class="surface" aria-label="图片预览底色">预览底色 <button type="button" data-surface="dark" aria-pressed="true">深底</button><button type="button" data-surface="light" aria-pressed="false">浅底</button><button type="button" data-surface="checker" aria-pressed="false">棋盘</button></div></div>
<div class="grid">__CARDS__</div><p class="empty" hidden>没有匹配的素材，请更换关键词或分类。</p></main>
<footer><p>原文件名、来源页、尺寸、实际格式、透明通道与 SHA-256 记录在 <a href="manifest.json">素材清单</a>。部分 Wiki PNG 地址返回 WebP，本地按实际格式保存，没有重新上色或转码。用途标签是本工程的候选建议。</p><p>终末地工业标志属于游戏图形；Endfield Talos Wiki 字标属于站点标识。各文件的来源与许可记录见 <a href="README.md">收集说明</a>。<a href="../endfield-wiki.zip" download>下载整包</a></p></footer>
<script>
const cards=[...document.querySelectorAll('.asset')];const search=document.querySelector('input[type=search]');let category='all';
function filter(){const query=search.value.trim().toLowerCase();let count=0;for(const card of cards){card.hidden=!((category==='all'||card.dataset.category===category)&&card.dataset.search.includes(query));if(!card.hidden)count++;}document.querySelector('#result-count').textContent=`显示 ${count} / ${cards.length} 项`;document.querySelector('.empty').hidden=count!==0;}
for(const button of document.querySelectorAll('[data-filter]'))button.addEventListener('click',()=>{category=button.dataset.filter;for(const other of document.querySelectorAll('[data-filter]'))other.setAttribute('aria-pressed',String(other===button));filter();});
for(const button of document.querySelectorAll('button[data-surface]'))button.addEventListener('click',()=>{document.body.dataset.surface=button.dataset.surface;for(const other of document.querySelectorAll('button[data-surface]'))other.setAttribute('aria-pressed',String(other===button));});search.addEventListener('input',filter);
</script></body></html>'''
    page = page.replace("__COUNT__", str(len(assets))).replace("__SIZE__", f"{total_size:.2f}")
    page = page.replace("__FILTERS__", controls).replace("__CARDS__", "\n".join(cards))
    (ASSETS / "index.html").write_text(page)
    archive = ROOT / "assets/endfield-wiki.zip"
    paths = [ASSETS / asset["path"] for asset in assets] + [ASSETS / name for name in ("manifest.json", "index.html", "README.md")]
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for path in paths:
            output.write(path, Path("endfield-wiki") / path.relative_to(ASSETS))
    print(json.dumps({"verified_assets": len(assets), "categories": counts,
                      "index": str(ASSETS / "index.html"), "zip": str(archive)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
