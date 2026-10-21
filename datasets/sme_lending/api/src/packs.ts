// Use packs (../../packs/), bundled when the Worker starts. Access follows docs/roles.html:
// public sees no packs, analyst sees every file except answer files, reviewer sees everything.
// When a dataset adds a pack or file, add it to PACK_FILES.

import aiEvalPrompts from '../../packs/ai-eval/prompts.md'
import aiEvalExpected from '../../packs/ai-eval/expected-answers.json'
import { RANK, type Role } from './db'

export type PackFile = {
  pack: string
  file: string
  description: string
  contentType: string
  minRole: Role
  body: string
}

export const PACK_FILES: PackFile[] = [
  {
    pack: 'ai-eval', file: 'prompts.md', description: 'Test questions to give the AI under test',
    contentType: 'text/markdown; charset=utf-8', minRole: 'analyst', body: aiEvalPrompts,
  },
  {
    pack: 'ai-eval', file: 'expected-answers.json', description: 'Expected answers and scoring notes (answer file)',
    contentType: 'application/json; charset=utf-8', minRole: 'reviewer', body: JSON.stringify(aiEvalExpected, null, 2),
  },
]

export const visiblePackFiles = (role: Role) => PACK_FILES.filter((f) => RANK[role] >= RANK[f.minRole])

export const findPackFile = (pack: string, file: string) => PACK_FILES.find((f) => f.pack === pack && f.file === file)
