const fs = require("fs");
const path = require("path");

// scripts/start.sh writes the generated package name here (it can differ per machine).
const { name } = JSON.parse(fs.readFileSync(path.join(__dirname, "graft-package.json"), "utf8"));
const { ArticlePipelineService, GraftConfig } = require(name);

// Point to our running Graftcode Gateway WebSocket
GraftConfig.host = process.env.GRAFT_HOST || "ws://localhost:8080/ws";

// Typed grafts return objects; older ones returned JSON strings. Accept both.
const j = (x) => (typeof x === "string" ? JSON.parse(x) : x);

async function main() {
  console.log("=== Testing Graftcode Python <-> Node.js RPC ===");
  try {
    const pipeline = new ArticlePipelineService();

    console.log("1. Calling pipeline.getPipelineStatus()...");
    const status = await pipeline.getPipelineStatus();
    console.log("Result:", j(status));

    console.log("\n2. Calling pipeline.listPendingTopics()...");
    const topicsRaw = await pipeline.listPendingTopics();
    const topics = j(topicsRaw);
    console.log(`Discovered ${topics.length} pending topics from Python review queue:`);
    topics.slice(0, 3).forEach((t, i) => {
      console.log(`  [${i+1}] ${t.title} (${t.category}) - ${t.sources_count} sources`);
    });

    console.log("\n3. Calling pipeline.suggestNextArticle()...");
    const suggestion = await pipeline.suggestNextArticle();
    console.log("Suggestion:", j(suggestion));

    console.log("\n4. Calling pipeline.runStyleCheck() on existing draft...");
    const draftsRaw = await pipeline.listDrafts();
    const drafts = j(draftsRaw);
    if (drafts.length > 0) {
      console.log(`Checking draft: ${drafts[0].filename}`);
      const audit = await pipeline.runStyleCheck(drafts[0].filename);
      console.log("Audit Result:", j(audit));
    }

    console.log("\n✅ SUCCESS: All Python methods executed natively from Node.js via Graftcode!");
    process.exit(0);
  } catch (err) {
    console.error("Test failed with error:", err);
    process.exit(1);
  }
}

main();
