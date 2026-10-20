import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'
import { ArticlePipelineService, GraftConfig } from '@graft/pypi-wayzyy_article_service_b3m8pn'

// Point to the live Graftcode Gateway WebSocket
GraftConfig.host = 'ws://localhost:8080/ws'

function graftcodeRpcPlugin(): Plugin {
  let pipeline: any = null

  return {
    name: 'graftcode-rpc-middleware',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url?.startsWith('/api/graft/')) {
          return next()
        }

        const method = req.url.replace('/api/graft/', '').split('?')[0]
        res.setHeader('Content-Type', 'application/json')
        res.setHeader('Access-Control-Allow-Origin', '*')
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type')

        if (req.method === 'OPTIONS') {
          res.statusCode = 204
          res.end()
          return
        }

        try {
          if (!pipeline) {
            pipeline = new ArticlePipelineService()
          }

          let body: any = {}
          if (req.method === 'POST') {
            const buffers = []
            for await (const chunk of req) {
              buffers.push(chunk)
            }
            const dataStr = Buffer.concat(buffers).toString()
            if (dataStr) {
              try {
                body = JSON.parse(dataStr)
              } catch {
                body = {}
              }
            }
          }

          const startTime = Date.now()
          let resultRaw = ''

          switch (method) {
            case 'getPipelineStatus':
              resultRaw = await pipeline.getPipelineStatus()
              break
            case 'listPendingTopics':
              resultRaw = await pipeline.listPendingTopics()
              break
            case 'getTopicSources':
              resultRaw = await pipeline.getTopicSources(body.topic || '')
              break
            case 'writeArticle':
              resultRaw = await pipeline.writeArticle(
                body.topic || 'Goa Vacation Rentals',
                body.skipResearch || false,
                body.extraResearch || ''
              )
              break
            case 'listDrafts':
              resultRaw = await pipeline.listDrafts()
              break
            case 'getDraft':
              resultRaw = await pipeline.getDraft(body.filename || '')
              break
            case 'saveDraft':
              resultRaw = await pipeline.saveDraft(body.filename || '', body.content || '')
              break
            case 'runStyleCheck':
              resultRaw = await pipeline.runStyleCheck(body.filename || '')
              break
            case 'runScanner':
              resultRaw = await pipeline.runScanner()
              break
            case 'suggestNextArticle':
              resultRaw = await pipeline.suggestNextArticle()
              break
            case 'pushToGithub':
              resultRaw = await pipeline.pushToGithub(body.filename || '')
              break
            default:
              res.statusCode = 404
              res.end(JSON.stringify({ error: `Method ${method} not found in ArticlePipelineService` }))
              return
          }

          const durationMs = Date.now() - startTime
          let parsedData
          try {
            parsedData = JSON.parse(resultRaw)
          } catch {
            parsedData = resultRaw
          }

          res.statusCode = 200
          res.end(
            JSON.stringify({
              success: true,
              method,
              durationMs,
              gateway: 'ws://localhost:8080/ws',
              transport: 'Hypertube Binary / WebSocket RPC',
              data: parsedData,
            })
          )
        } catch (error: any) {
          console.error(`Graftcode RPC Error (${method}):`, error)
          res.statusCode = 500
          res.end(
            JSON.stringify({
              success: false,
              method,
              error: error?.message || String(error),
              hint: 'Verify that Graftcode Gateway is running on ws://localhost:8080/ws',
            })
          )
        }
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), graftcodeRpcPlugin()],
  server: {
    port: 5173,
  },
})
