// 'graft-client' is an alias for the generated Graft package; vite.config.ts maps it
// to the package name that scripts/start.sh recorded in graft-package.json.
declare module 'graft-client' {
  export const GraftConfig: { host: string }
  export class ArticlePipelineService {
    constructor()
    [method: string]: (...args: any[]) => Promise<any>
  }
}
