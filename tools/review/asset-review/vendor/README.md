# vendor/

`three.bundle.js` (about 800 KB, three.js r186 + GLTFLoader + GLTFExporter, MIT) is not committed;
it is a third-party build output. Rebuild it once per machine before running `asset_review.py`:

```powershell
cd <pipeline>\tools\review\asset-review\vendor
npm init -y; npm install three@0.186.0 esbuild@0.25.0
npx esbuild three_entry.js --bundle --format=esm --minify --outfile=three.bundle.js
Remove-Item -Recurse node_modules, package.json, package-lock.json
```

The XCOM original lives at `S:/Repos/OpenXcom-Extended-3D/art/tools/asset-review/vendor/three.bundle.js`;
copying it is equally fine. `.gitignore` excludes the bundle.
