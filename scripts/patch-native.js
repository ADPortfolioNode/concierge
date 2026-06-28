const fs = require("fs");
const path = require("path");
function patch(parent, binding, ver) {
  const p = path.join("node_modules", parent, "package.json");
  if (fs.existsSync(p)) {
    const pkg = JSON.parse(fs.readFileSync(p, "utf8"));
    pkg.optionalDependencies = pkg.optionalDependencies || {};
    pkg.optionalDependencies[binding] = ver;
    fs.writeFileSync(p, JSON.stringify(pkg, null, 2));
    console.log("Patched", parent);
  }
}
patch("@tailwindcss/oxide", "@tailwindcss/oxide-linux-x64-musl", "4.2.1");
patch("lightningcss", "lightningcss-linux-x64-musl", "1.31.1");
patch("rollup", "@rollup/rollup-linux-x64-musl", "4.59.0");