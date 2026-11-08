"""Optional document-render test; WeasyPrint needed only for PDF verification."""
import importlib.util
import subprocess
import unittest
from pathlib import Path

@unittest.skipUnless(importlib.util.find_spec("weasyprint"), "Optional WeasyPrint not installed")
class BriefLayout(unittest.TestCase):
    def test_normal_apopka_ml_brief_stays_one_page(self):
        from weasyprint import HTML
        app = Path(__file__).resolve().parents[1] / "app"
        code = """
import fs from 'node:fs';
import { briefHTML } from './src/domain.js';
const {tracts}=JSON.parse(fs.readFileSync('public/data/tracts.json'));
const {rows}=JSON.parse(fs.readFileSync('public/data/snap_gap.json'));
const metadata=JSON.parse(fs.readFileSync('public/data/metadata.json'));
const t=tracts.find(t=>t.geoid==='12095017703');
t.snap_gap=rows.find(r=>r.geoid===t.geoid);
const events=[
{kind:'decision',geoid:t.geoid,reviewer:'Organizer',decision:'approve',reason:'Verify existing services and capacity before selecting a site.'},
{kind:'note',geoid:t.geoid,reviewer:'Organizer',demo:true,text:'DEMO INPUT (unverified): church on Main St already runs a Tuesday pantry here.'},
{kind:'assignment',geoid:t.geoid,reviewer:'Organizer',owner:'Volunteer 1 (demo)',status:'Assigned'}];
console.log(briefHTML(t,{events,order:[]},'sd',false,{...metadata,demo:true}));
"""
        html = subprocess.run(["node", "--input-type=module", "-e", code], cwd=app, text=True, capture_output=True, check=True).stdout
        doc = HTML(string=html).render()
        self.assertEqual(len(doc.pages), 1, "ML section pushes a normal decision brief onto page two")
        visible = " ".join(box.text for page in doc.pages for box in page._page_box.descendants() if hasattr(box, "text"))
        self.assertIn("About 22 in 100", visible)
        self.assertNotIn("Five-fold held-out ridge", visible)
        self.assertNotIn("Top model associations", visible)

if __name__ == "__main__": unittest.main()
