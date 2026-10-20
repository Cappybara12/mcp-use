const { ArticlePipelineService, GraftConfig } = require("@graft/pypi-wayzyy_article_service_b3m8pn");

// Point to our running Graftcode Gateway WebSocket
GraftConfig.host = "ws://localhost:8080/ws";

async function main() {
  console.log("=== Testing Graftcode Python <-> Node.js RPC ===");
  try {
    const pipeline = new ArticlePipelineService();

    console.log("1. Calling pipeline.getPipelineStatus()...");
    const status = await pipeline.getPipelineStatus();
    console.log("Result:", JSON.parse(status));

    console.log("\n2. Calling pipeline.listPendingTopics()...");
    const topicsRaw = await pipeline.listPendingTopics();
    const topics = JSON.parse(topicsRaw);
    console.log(`Discovered ${topics.length} pending topics from Python review queue:`);
    topics.slice(0, 3).forEach((t, i) => {
      console.log(`  [${i+1}] ${t.title} (${t.category}) - ${t.sources_count} sources`);
    });

    console.log("\n3. Calling pipeline.suggestNextArticle()...");
    const suggestion = await pipeline.suggestNextArticle();
    console.log("Suggestion:", JSON.parse(suggestion));

    console.log("\n4. Calling pipeline.runStyleCheck() on existing draft...");
    const draftsRaw = await pipeline.listDrafts();
    const drafts = JSON.parse(draftsRaw);
    if (drafts.length > 0) {
      console.log(`Checking draft: ${drafts[0].filename}`);
      const audit = await pipeline.runStyleCheck(drafts[0].filename);
      console.log("Audit Result:", JSON.parse(audit));
    }

    console.log("\n✅ SUCCESS: All Python methods executed natively from Node.js via Graftcode!");
    process.exit(0);
  } catch (err) {
    console.error("Test failed with error:", err);
    process.exit(1);
  }
}

main();
