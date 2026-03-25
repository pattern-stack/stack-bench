import type { FileTreeNode, FileContent } from "@/types/file-tree";

export const mockFileTree: FileTreeNode = {
  "name": "stack-bench",
  "path": "",
  "type": "dir",
  "size": null,
  "children": [
    {
      "name": ".claude",
      "path": ".claude",
      "type": "dir",
      "size": null,
      "children": [
        {
          "name": "agents",
          "path": ".claude/agents",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "browser-pilot.md",
              "path": ".claude/agents/browser-pilot.md",
              "type": "file",
              "size": 5089,
              "children": null
            }
          ]
        },
        {
          "name": "commands",
          "path": ".claude/commands",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "build.md",
              "path": ".claude/commands/build.md",
              "type": "file",
              "size": 248,
              "children": null
            },
            {
              "name": "develop.md",
              "path": ".claude/commands/develop.md",
              "type": "file",
              "size": 3774,
              "children": null
            },
            {
              "name": "orchestrate.md",
              "path": ".claude/commands/orchestrate.md",
              "type": "file",
              "size": 3599,
              "children": null
            },
            {
              "name": "plan.md",
              "path": ".claude/commands/plan.md",
              "type": "file",
              "size": 1711,
              "children": null
            },
            {
              "name": "plan_w_team.md",
              "path": ".claude/commands/plan_w_team.md",
              "type": "file",
              "size": 778,
              "children": null
            },
            {
              "name": "prime.md",
              "path": ".claude/commands/prime.md",
              "type": "file",
              "size": 4861,
              "children": null
            }
          ]
        },
        {
          "name": "docs",
          "path": ".claude/docs",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "domain-model-expansion.md",
              "path": ".claude/docs/domain-model-expansion.md",
              "type": "file",
              "size": 236,
              "children": null
            },
            {
              "name": "primer-addendum.md",
              "path": ".claude/docs/primer-addendum.md",
              "type": "file",
              "size": 5062,
              "children": null
            },
            {
              "name": "primer.md",
              "path": ".claude/docs/primer.md",
              "type": "file",
              "size": 2797,
              "children": null
            }
          ]
        },
        {
          "name": "primitives",
          "path": ".claude/primitives",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "README.md",
              "path": ".claude/primitives/README.md",
              "type": "file",
              "size": 1389,
              "children": null
            },
            {
              "name": "session-logging.md",
              "path": ".claude/primitives/session-logging.md",
              "type": "file",
              "size": 3500,
              "children": null
            },
            {
              "name": "session-state.md",
              "path": ".claude/primitives/session-state.md",
              "type": "file",
              "size": 441,
              "children": null
            }
          ]
        },
        {
          "name": "sdlc.yml",
          "path": ".claude/sdlc.yml",
          "type": "file",
          "size": 3919,
          "children": null
        },
        {
          "name": "settings.json",
          "path": ".claude/settings.json",
          "type": "file",
          "size": 2419,
          "children": null
        },
        {
          "name": "skills",
          "path": ".claude/skills",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "pattern-stack",
              "path": ".claude/skills/pattern-stack",
              "type": "file",
              "size": 602,
              "children": null
            }
          ]
        },
        {
          "name": "specs",
          "path": ".claude/specs",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "2026-03-21-file-viewer.md",
              "path": ".claude/specs/2026-03-21-file-viewer.md",
              "type": "file",
              "size": 2702,
              "children": null
            },
            {
              "name": "2026-03-21-shiki-diff-highlighting.md",
              "path": ".claude/specs/2026-03-21-shiki-diff-highlighting.md",
              "type": "file",
              "size": 4209,
              "children": null
            },
            {
              "name": "sb-035-frontend-scaffold.md",
              "path": ".claude/specs/sb-035-frontend-scaffold.md",
              "type": "file",
              "size": 4659,
              "children": null
            },
            {
              "name": "sb-036-shared-atoms.md",
              "path": ".claude/specs/sb-036-shared-atoms.md",
              "type": "file",
              "size": 3804,
              "children": null
            },
            {
              "name": "sb-037-stack-navigation.md",
              "path": ".claude/specs/sb-037-stack-navigation.md",
              "type": "file",
              "size": 1396,
              "children": null
            },
            {
              "name": "sb-038-app-shell.md",
              "path": ".claude/specs/sb-038-app-shell.md",
              "type": "file",
              "size": 3869,
              "children": null
            },
            {
              "name": "sb-039-diff-review.md",
              "path": ".claude/specs/sb-039-diff-review.md",
              "type": "file",
              "size": 3458,
              "children": null
            }
          ]
        }
      ]
    },
    {
      "name": ".env.example",
      "path": ".env.example",
      "type": "file",
      "size": 3965,
      "children": null
    },
    {
      "name": ".github",
      "path": ".github",
      "type": "dir",
      "size": null,
      "children": [
        {
          "name": "workflows",
          "path": ".github/workflows",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "ci.yml",
              "path": ".github/workflows/ci.yml",
              "type": "file",
              "size": 4336,
              "children": null
            },
            {
              "name": "claude-code-review.yml",
              "path": ".github/workflows/claude-code-review.yml",
              "type": "file",
              "size": 3726,
              "children": null
            },
            {
              "name": "claude.yml",
              "path": ".github/workflows/claude.yml",
              "type": "file",
              "size": 2048,
              "children": null
            }
          ]
        }
      ]
    },
    {
      "name": ".gitignore",
      "path": ".gitignore",
      "type": "file",
      "size": 2377,
      "children": null
    },
    {
      "name": ".mise.toml",
      "path": ".mise.toml",
      "type": "file",
      "size": 5038,
      "children": null
    },
    {
      "name": "CLAUDE.md",
      "path": "CLAUDE.md",
      "type": "file",
      "size": 4650,
      "children": null
    },
    {
      "name": "Justfile",
      "path": "Justfile",
      "type": "file",
      "size": 839,
      "children": null
    },
    {
      "name": "app",
      "path": "app",
      "type": "dir",
      "size": null,
      "children": [
        {
          "name": "backend",
          "path": "app/backend",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": ".env.example",
              "path": "app/backend/.env.example",
              "type": "file",
              "size": 867,
              "children": null
            },
            {
              "name": ".gitignore",
              "path": "app/backend/.gitignore",
              "type": "file",
              "size": 4434,
              "children": null
            },
            {
              "name": "Justfile",
              "path": "app/backend/Justfile",
              "type": "file",
              "size": 3551,
              "children": null
            },
            {
              "name": "__tests__",
              "path": "app/backend/__tests__",
              "type": "dir",
              "size": null,
              "children": [
                {
                  "name": "__init__.py",
                  "path": "app/backend/__tests__/__init__.py",
                  "type": "file",
                  "size": 1279,
                  "children": null
                },
                {
                  "name": "conftest.py",
                  "path": "app/backend/__tests__/conftest.py",
                  "type": "file",
                  "size": 643,
                  "children": null
                },
                {
                  "name": "test_health.py",
                  "path": "app/backend/__tests__/test_health.py",
                  "type": "file",
                  "size": 2636,
                  "children": null
                },
                {
                  "name": "test_seed.py",
                  "path": "app/backend/__tests__/test_seed.py",
                  "type": "file",
                  "size": 1844,
                  "children": null
                }
              ]
            },
            {
              "name": "alembic.ini",
              "path": "app/backend/alembic.ini",
              "type": "file",
              "size": 574,
              "children": null
            },
            {
              "name": "alembic",
              "path": "app/backend/alembic",
              "type": "dir",
              "size": null,
              "children": [
                {
                  "name": "env.py",
                  "path": "app/backend/alembic/env.py",
                  "type": "file",
                  "size": 2280,
                  "children": null
                },
                {
                  "name": "script.py.mako",
                  "path": "app/backend/alembic/script.py.mako",
                  "type": "file",
                  "size": 612,
                  "children": null
                }
              ]
            },
            {
              "name": "pyproject.toml",
              "path": "app/backend/pyproject.toml",
              "type": "file",
              "size": 3386,
              "children": null
            },
            {
              "name": "src",
              "path": "app/backend/src",
              "type": "dir",
              "size": null,
              "children": [
                {
                  "name": "config",
                  "path": "app/backend/src/config",
                  "type": "dir",
                  "size": null,
                  "children": [
                    {
                      "name": "__init__.py",
                      "path": "app/backend/src/config/__init__.py",
                      "type": "file",
                      "size": 2893,
                      "children": null
                    },
                    {
                      "name": "settings.py",
                      "path": "app/backend/src/config/settings.py",
                      "type": "file",
                      "size": 487,
                      "children": null
                    }
                  ]
                },
                {
                  "name": "features",
                  "path": "app/backend/src/features",
                  "type": "dir",
                  "size": null,
                  "children": [
                    {
                      "name": "__init__.py",
                      "path": "app/backend/src/features/__init__.py",
                      "type": "file",
                      "size": 3707,
                      "children": null
                    },
                    {
                      "name": "agent_definitions",
                      "path": "app/backend/src/features/agent_definitions",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/agent_definitions/__init__.py",
                          "type": "file",
                          "size": 2908,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/agent_definitions/models.py",
                          "type": "file",
                          "size": 463,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/agent_definitions/service.py",
                          "type": "file",
                          "size": 1477,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "agent_runs",
                      "path": "app/backend/src/features/agent_runs",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/agent_runs/__init__.py",
                          "type": "file",
                          "size": 2700,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/agent_runs/models.py",
                          "type": "file",
                          "size": 3522,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/agent_runs/service.py",
                          "type": "file",
                          "size": 1598,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "branches",
                      "path": "app/backend/src/features/branches",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/branches/__init__.py",
                          "type": "file",
                          "size": 4783,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/branches/models.py",
                          "type": "file",
                          "size": 425,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/branches/service.py",
                          "type": "file",
                          "size": 922,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "conversations",
                      "path": "app/backend/src/features/conversations",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/conversations/__init__.py",
                          "type": "file",
                          "size": 4912,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/conversations/models.py",
                          "type": "file",
                          "size": 3945,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/conversations/service.py",
                          "type": "file",
                          "size": 719,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "jobs",
                      "path": "app/backend/src/features/jobs",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/jobs/__init__.py",
                          "type": "file",
                          "size": 213,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/jobs/models.py",
                          "type": "file",
                          "size": 2815,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/jobs/service.py",
                          "type": "file",
                          "size": 2781,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "message_parts",
                      "path": "app/backend/src/features/message_parts",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/message_parts/__init__.py",
                          "type": "file",
                          "size": 2537,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/message_parts/models.py",
                          "type": "file",
                          "size": 2379,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/message_parts/service.py",
                          "type": "file",
                          "size": 588,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "messages",
                      "path": "app/backend/src/features/messages",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/messages/__init__.py",
                          "type": "file",
                          "size": 3669,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/messages/models.py",
                          "type": "file",
                          "size": 2773,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/messages/service.py",
                          "type": "file",
                          "size": 1651,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "projects",
                      "path": "app/backend/src/features/projects",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/projects/__init__.py",
                          "type": "file",
                          "size": 4049,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/projects/models.py",
                          "type": "file",
                          "size": 2261,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/projects/service.py",
                          "type": "file",
                          "size": 1478,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "pull_requests",
                      "path": "app/backend/src/features/pull_requests",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/pull_requests/__init__.py",
                          "type": "file",
                          "size": 626,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/pull_requests/models.py",
                          "type": "file",
                          "size": 4508,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/pull_requests/service.py",
                          "type": "file",
                          "size": 740,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "role_templates",
                      "path": "app/backend/src/features/role_templates",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/role_templates/__init__.py",
                          "type": "file",
                          "size": 1722,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/role_templates/models.py",
                          "type": "file",
                          "size": 1046,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/role_templates/service.py",
                          "type": "file",
                          "size": 2622,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "stacks",
                      "path": "app/backend/src/features/stacks",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/stacks/__init__.py",
                          "type": "file",
                          "size": 4322,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/stacks/models.py",
                          "type": "file",
                          "size": 2322,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/stacks/service.py",
                          "type": "file",
                          "size": 1811,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "tool_calls",
                      "path": "app/backend/src/features/tool_calls",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/tool_calls/__init__.py",
                          "type": "file",
                          "size": 3716,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/tool_calls/models.py",
                          "type": "file",
                          "size": 1189,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/tool_calls/service.py",
                          "type": "file",
                          "size": 3807,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "workspaces",
                      "path": "app/backend/src/features/workspaces",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/features/workspaces/__init__.py",
                          "type": "file",
                          "size": 4005,
                          "children": null
                        },
                        {
                          "name": "models.py",
                          "path": "app/backend/src/features/workspaces/models.py",
                          "type": "file",
                          "size": 3883,
                          "children": null
                        },
                        {
                          "name": "service.py",
                          "path": "app/backend/src/features/workspaces/service.py",
                          "type": "file",
                          "size": 3505,
                          "children": null
                        }
                      ]
                    }
                  ]
                },
                {
                  "name": "molecules",
                  "path": "app/backend/src/molecules",
                  "type": "dir",
                  "size": null,
                  "children": [
                    {
                      "name": "__init__.py",
                      "path": "app/backend/src/molecules/__init__.py",
                      "type": "file",
                      "size": 4965,
                      "children": null
                    },
                    {
                      "name": "agents",
                      "path": "app/backend/src/molecules/agents",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/molecules/agents/__init__.py",
                          "type": "file",
                          "size": 2892,
                          "children": null
                        },
                        {
                          "name": "assembler.py",
                          "path": "app/backend/src/molecules/agents/assembler.py",
                          "type": "file",
                          "size": 3170,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "apis",
                      "path": "app/backend/src/molecules/apis",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/molecules/apis/__init__.py",
                          "type": "file",
                          "size": 2890,
                          "children": null
                        },
                        {
                          "name": "conversation_api.py",
                          "path": "app/backend/src/molecules/apis/conversation_api.py",
                          "type": "file",
                          "size": 3249,
                          "children": null
                        },
                        {
                          "name": "stack_api.py",
                          "path": "app/backend/src/molecules/apis/stack_api.py",
                          "type": "file",
                          "size": 3485,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "entities",
                      "path": "app/backend/src/molecules/entities",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/molecules/entities/__init__.py",
                          "type": "file",
                          "size": 3161,
                          "children": null
                        },
                        {
                          "name": "conversation_entity.py",
                          "path": "app/backend/src/molecules/entities/conversation_entity.py",
                          "type": "file",
                          "size": 1302,
                          "children": null
                        },
                        {
                          "name": "stack_entity.py",
                          "path": "app/backend/src/molecules/entities/stack_entity.py",
                          "type": "file",
                          "size": 3012,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "exceptions.py",
                      "path": "app/backend/src/molecules/exceptions.py",
                      "type": "file",
                      "size": 1420,
                      "children": null
                    },
                    {
                      "name": "providers",
                      "path": "app/backend/src/molecules/providers",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/molecules/providers/__init__.py",
                          "type": "file",
                          "size": 2040,
                          "children": null
                        },
                        {
                          "name": "stack_cli_adapter.py",
                          "path": "app/backend/src/molecules/providers/stack_cli_adapter.py",
                          "type": "file",
                          "size": 1241,
                          "children": null
                        },
                        {
                          "name": "stack_provider.py",
                          "path": "app/backend/src/molecules/providers/stack_provider.py",
                          "type": "file",
                          "size": 2706,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "runtime",
                      "path": "app/backend/src/molecules/runtime",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/molecules/runtime/__init__.py",
                          "type": "file",
                          "size": 3783,
                          "children": null
                        },
                        {
                          "name": "conversation_runner.py",
                          "path": "app/backend/src/molecules/runtime/conversation_runner.py",
                          "type": "file",
                          "size": 3723,
                          "children": null
                        }
                      ]
                    }
                  ]
                },
                {
                  "name": "organisms",
                  "path": "app/backend/src/organisms",
                  "type": "dir",
                  "size": null,
                  "children": [
                    {
                      "name": "__init__.py",
                      "path": "app/backend/src/organisms/__init__.py",
                      "type": "file",
                      "size": 2329,
                      "children": null
                    },
                    {
                      "name": "api",
                      "path": "app/backend/src/organisms/api",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/organisms/api/__init__.py",
                          "type": "file",
                          "size": 1917,
                          "children": null
                        },
                        {
                          "name": "app.py",
                          "path": "app/backend/src/organisms/api/app.py",
                          "type": "file",
                          "size": 4371,
                          "children": null
                        },
                        {
                          "name": "dependencies.py",
                          "path": "app/backend/src/organisms/api/dependencies.py",
                          "type": "file",
                          "size": 523,
                          "children": null
                        },
                        {
                          "name": "error_handlers.py",
                          "path": "app/backend/src/organisms/api/error_handlers.py",
                          "type": "file",
                          "size": 3534,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "cli",
                      "path": "app/backend/src/organisms/cli",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "__init__.py",
                          "path": "app/backend/src/organisms/cli/__init__.py",
                          "type": "file",
                          "size": 2559,
                          "children": null
                        }
                      ]
                    }
                  ]
                },
                {
                  "name": "seeds",
                  "path": "app/backend/src/seeds",
                  "type": "dir",
                  "size": null,
                  "children": [
                    {
                      "name": "__init__.py",
                      "path": "app/backend/src/seeds/__init__.py",
                      "type": "file",
                      "size": 2104,
                      "children": null
                    },
                    {
                      "name": "agents.yaml",
                      "path": "app/backend/src/seeds/agents.yaml",
                      "type": "file",
                      "size": 866,
                      "children": null
                    },
                    {
                      "name": "specs.py",
                      "path": "app/backend/src/seeds/specs.py",
                      "type": "file",
                      "size": 3034,
                      "children": null
                    }
                  ]
                }
              ]
            },
            {
              "name": "uv.lock",
              "path": "app/backend/uv.lock",
              "type": "file",
              "size": 3386,
              "children": null
            }
          ]
        },
        {
          "name": "cli",
          "path": "app/cli",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "Justfile",
              "path": "app/cli/Justfile",
              "type": "file",
              "size": 3025,
              "children": null
            },
            {
              "name": "go.mod",
              "path": "app/cli/go.mod",
              "type": "file",
              "size": 1631,
              "children": null
            },
            {
              "name": "go.sum",
              "path": "app/cli/go.sum",
              "type": "file",
              "size": 3420,
              "children": null
            },
            {
              "name": "main.go",
              "path": "app/cli/main.go",
              "type": "file",
              "size": 2943,
              "children": null
            }
          ]
        },
        {
          "name": "frontend",
          "path": "app/frontend",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "index.html",
              "path": "app/frontend/index.html",
              "type": "file",
              "size": 3891,
              "children": null
            },
            {
              "name": "package-lock.json",
              "path": "app/frontend/package-lock.json",
              "type": "file",
              "size": 3833,
              "children": null
            },
            {
              "name": "package.json",
              "path": "app/frontend/package.json",
              "type": "file",
              "size": 300,
              "children": null
            },
            {
              "name": "src",
              "path": "app/frontend/src",
              "type": "dir",
              "size": null,
              "children": [
                {
                  "name": "App.tsx",
                  "path": "app/frontend/src/App.tsx",
                  "type": "file",
                  "size": 1089,
                  "children": null
                },
                {
                  "name": "components",
                  "path": "app/frontend/src/components",
                  "type": "dir",
                  "size": null,
                  "children": [
                    {
                      "name": "atoms",
                      "path": "app/frontend/src/components/atoms",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "Badge",
                          "path": "app/frontend/src/components/atoms/Badge",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "Badge.tsx",
                              "path": "app/frontend/src/components/atoms/Badge/Badge.tsx",
                              "type": "file",
                              "size": 238,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/Badge/index.ts",
                              "type": "file",
                              "size": 4739,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "BranchMeta",
                          "path": "app/frontend/src/components/atoms/BranchMeta",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "BranchMeta.tsx",
                              "path": "app/frontend/src/components/atoms/BranchMeta/BranchMeta.tsx",
                              "type": "file",
                              "size": 745,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/BranchMeta/index.ts",
                              "type": "file",
                              "size": 3976,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "Button",
                          "path": "app/frontend/src/components/atoms/Button",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "Button.tsx",
                              "path": "app/frontend/src/components/atoms/Button/Button.tsx",
                              "type": "file",
                              "size": 3193,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/Button/index.ts",
                              "type": "file",
                              "size": 4363,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "Collapsible",
                          "path": "app/frontend/src/components/atoms/Collapsible",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "Collapsible.tsx",
                              "path": "app/frontend/src/components/atoms/Collapsible/Collapsible.tsx",
                              "type": "file",
                              "size": 3255,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/Collapsible/index.ts",
                              "type": "file",
                              "size": 3203,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "DiffBadge",
                          "path": "app/frontend/src/components/atoms/DiffBadge",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "DiffBadge.tsx",
                              "path": "app/frontend/src/components/atoms/DiffBadge/DiffBadge.tsx",
                              "type": "file",
                              "size": 492,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/DiffBadge/index.ts",
                              "type": "file",
                              "size": 3844,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "DiffLine",
                          "path": "app/frontend/src/components/atoms/DiffLine",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "DiffLine.tsx",
                              "path": "app/frontend/src/components/atoms/DiffLine/DiffLine.tsx",
                              "type": "file",
                              "size": 3590,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/DiffLine/index.ts",
                              "type": "file",
                              "size": 2319,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "DiffStat",
                          "path": "app/frontend/src/components/atoms/DiffStat",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "DiffStat.tsx",
                              "path": "app/frontend/src/components/atoms/DiffStat/DiffStat.tsx",
                              "type": "file",
                              "size": 1035,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/DiffStat/index.ts",
                              "type": "file",
                              "size": 3404,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "FileIcon",
                          "path": "app/frontend/src/components/atoms/FileIcon",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "FileIcon.tsx",
                              "path": "app/frontend/src/components/atoms/FileIcon/FileIcon.tsx",
                              "type": "file",
                              "size": 4036,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/FileIcon/index.ts",
                              "type": "file",
                              "size": 139,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "Icon",
                          "path": "app/frontend/src/components/atoms/Icon",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "Icon.tsx",
                              "path": "app/frontend/src/components/atoms/Icon/Icon.tsx",
                              "type": "file",
                              "size": 589,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/Icon/index.ts",
                              "type": "file",
                              "size": 1476,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "IndentGuide",
                          "path": "app/frontend/src/components/atoms/IndentGuide",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "IndentGuide.tsx",
                              "path": "app/frontend/src/components/atoms/IndentGuide/IndentGuide.tsx",
                              "type": "file",
                              "size": 1036,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/IndentGuide/index.ts",
                              "type": "file",
                              "size": 2413,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "SearchInput",
                          "path": "app/frontend/src/components/atoms/SearchInput",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "SearchInput.tsx",
                              "path": "app/frontend/src/components/atoms/SearchInput/SearchInput.tsx",
                              "type": "file",
                              "size": 611,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/SearchInput/index.ts",
                              "type": "file",
                              "size": 2177,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "StackDot",
                          "path": "app/frontend/src/components/atoms/StackDot",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "StackDot.tsx",
                              "path": "app/frontend/src/components/atoms/StackDot/StackDot.tsx",
                              "type": "file",
                              "size": 696,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/StackDot/index.ts",
                              "type": "file",
                              "size": 762,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "Tab",
                          "path": "app/frontend/src/components/atoms/Tab",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "CountBadge.tsx",
                              "path": "app/frontend/src/components/atoms/Tab/CountBadge.tsx",
                              "type": "file",
                              "size": 2976,
                              "children": null
                            },
                            {
                              "name": "Tab.tsx",
                              "path": "app/frontend/src/components/atoms/Tab/Tab.tsx",
                              "type": "file",
                              "size": 5041,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/atoms/Tab/index.ts",
                              "type": "file",
                              "size": 3048,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "index.ts",
                          "path": "app/frontend/src/components/atoms/index.ts",
                          "type": "file",
                          "size": 139,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "molecules",
                      "path": "app/frontend/src/components/molecules",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "ActionBar",
                          "path": "app/frontend/src/components/molecules/ActionBar",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "ActionBar.tsx",
                              "path": "app/frontend/src/components/molecules/ActionBar/ActionBar.tsx",
                              "type": "file",
                              "size": 595,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/ActionBar/index.ts",
                              "type": "file",
                              "size": 3243,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "DiffFile",
                          "path": "app/frontend/src/components/molecules/DiffFile",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "DiffFile.tsx",
                              "path": "app/frontend/src/components/molecules/DiffFile/DiffFile.tsx",
                              "type": "file",
                              "size": 3526,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/DiffFile/index.ts",
                              "type": "file",
                              "size": 1572,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "DiffFileHeader",
                          "path": "app/frontend/src/components/molecules/DiffFileHeader",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "DiffFileHeader.tsx",
                              "path": "app/frontend/src/components/molecules/DiffFileHeader/DiffFileHeader.tsx",
                              "type": "file",
                              "size": 298,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/DiffFileHeader/index.ts",
                              "type": "file",
                              "size": 4893,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "DiffHunk",
                          "path": "app/frontend/src/components/molecules/DiffHunk",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "DiffHunk.tsx",
                              "path": "app/frontend/src/components/molecules/DiffHunk/DiffHunk.tsx",
                              "type": "file",
                              "size": 141,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/DiffHunk/index.ts",
                              "type": "file",
                              "size": 2680,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "ExplorerToolbar",
                          "path": "app/frontend/src/components/molecules/ExplorerToolbar",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "ExplorerToolbar.tsx",
                              "path": "app/frontend/src/components/molecules/ExplorerToolbar/ExplorerToolbar.tsx",
                              "type": "file",
                              "size": 3904,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/ExplorerToolbar/index.ts",
                              "type": "file",
                              "size": 3732,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "FileContent",
                          "path": "app/frontend/src/components/molecules/FileContent",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "FileContent.tsx",
                              "path": "app/frontend/src/components/molecules/FileContent/FileContent.tsx",
                              "type": "file",
                              "size": 216,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/FileContent/index.ts",
                              "type": "file",
                              "size": 4955,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "FileListSummary",
                          "path": "app/frontend/src/components/molecules/FileListSummary",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "FileListSummary.tsx",
                              "path": "app/frontend/src/components/molecules/FileListSummary/FileListSummary.tsx",
                              "type": "file",
                              "size": 242,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/FileListSummary/index.ts",
                              "type": "file",
                              "size": 434,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "FileTreeItem",
                          "path": "app/frontend/src/components/molecules/FileTreeItem",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "FileTreeItem.tsx",
                              "path": "app/frontend/src/components/molecules/FileTreeItem/FileTreeItem.tsx",
                              "type": "file",
                              "size": 1655,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/FileTreeItem/index.ts",
                              "type": "file",
                              "size": 3311,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "PRHeader",
                          "path": "app/frontend/src/components/molecules/PRHeader",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "PRHeader.tsx",
                              "path": "app/frontend/src/components/molecules/PRHeader/PRHeader.tsx",
                              "type": "file",
                              "size": 3362,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/PRHeader/index.ts",
                              "type": "file",
                              "size": 5080,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "PathBar",
                          "path": "app/frontend/src/components/molecules/PathBar",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "PathBar.tsx",
                              "path": "app/frontend/src/components/molecules/PathBar/PathBar.tsx",
                              "type": "file",
                              "size": 409,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/PathBar/index.ts",
                              "type": "file",
                              "size": 4276,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "StackConnector",
                          "path": "app/frontend/src/components/molecules/StackConnector",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "StackConnector.tsx",
                              "path": "app/frontend/src/components/molecules/StackConnector/StackConnector.tsx",
                              "type": "file",
                              "size": 1904,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/StackConnector/index.ts",
                              "type": "file",
                              "size": 3278,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "StackItem",
                          "path": "app/frontend/src/components/molecules/StackItem",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "StackItem.tsx",
                              "path": "app/frontend/src/components/molecules/StackItem/StackItem.tsx",
                              "type": "file",
                              "size": 5059,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/StackItem/index.ts",
                              "type": "file",
                              "size": 1065,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "StatusBadge",
                          "path": "app/frontend/src/components/molecules/StatusBadge",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "StatusBadge.tsx",
                              "path": "app/frontend/src/components/molecules/StatusBadge/StatusBadge.tsx",
                              "type": "file",
                              "size": 2821,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/StatusBadge/index.ts",
                              "type": "file",
                              "size": 4753,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "TabBar",
                          "path": "app/frontend/src/components/molecules/TabBar",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "TabBar.tsx",
                              "path": "app/frontend/src/components/molecules/TabBar/TabBar.tsx",
                              "type": "file",
                              "size": 500,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/molecules/TabBar/index.ts",
                              "type": "file",
                              "size": 3103,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "index.ts",
                          "path": "app/frontend/src/components/molecules/index.ts",
                          "type": "file",
                          "size": 4409,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "organisms",
                      "path": "app/frontend/src/components/organisms",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "FileTree",
                          "path": "app/frontend/src/components/organisms/FileTree",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "FileTree.tsx",
                              "path": "app/frontend/src/components/organisms/FileTree/FileTree.tsx",
                              "type": "file",
                              "size": 975,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/organisms/FileTree/index.ts",
                              "type": "file",
                              "size": 1137,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "FileViewerPanel",
                          "path": "app/frontend/src/components/organisms/FileViewerPanel",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "FileViewerPanel.tsx",
                              "path": "app/frontend/src/components/organisms/FileViewerPanel/FileViewerPanel.tsx",
                              "type": "file",
                              "size": 2940,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/organisms/FileViewerPanel/index.ts",
                              "type": "file",
                              "size": 3257,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "FilesChangedPanel",
                          "path": "app/frontend/src/components/organisms/FilesChangedPanel",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "FilesChangedPanel.tsx",
                              "path": "app/frontend/src/components/organisms/FilesChangedPanel/FilesChangedPanel.tsx",
                              "type": "file",
                              "size": 3345,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/organisms/FilesChangedPanel/index.ts",
                              "type": "file",
                              "size": 3128,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "StackSidebar",
                          "path": "app/frontend/src/components/organisms/StackSidebar",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "StackSidebar.tsx",
                              "path": "app/frontend/src/components/organisms/StackSidebar/StackSidebar.tsx",
                              "type": "file",
                              "size": 188,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/organisms/StackSidebar/index.ts",
                              "type": "file",
                              "size": 1561,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "index.ts",
                          "path": "app/frontend/src/components/organisms/index.ts",
                          "type": "file",
                          "size": 3850,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "templates",
                      "path": "app/frontend/src/components/templates",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "AppShell",
                          "path": "app/frontend/src/components/templates/AppShell",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "AppShell.tsx",
                              "path": "app/frontend/src/components/templates/AppShell/AppShell.tsx",
                              "type": "file",
                              "size": 3448,
                              "children": null
                            },
                            {
                              "name": "index.ts",
                              "path": "app/frontend/src/components/templates/AppShell/index.ts",
                              "type": "file",
                              "size": 3677,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "index.ts",
                          "path": "app/frontend/src/components/templates/index.ts",
                          "type": "file",
                          "size": 504,
                          "children": null
                        }
                      ]
                    }
                  ]
                },
                {
                  "name": "generated",
                  "path": "app/frontend/src/generated",
                  "type": "dir",
                  "size": null,
                  "children": [
                    {
                      "name": ".gitkeep",
                      "path": "app/frontend/src/generated/.gitkeep",
                      "type": "file",
                      "size": 2551,
                      "children": null
                    }
                  ]
                },
                {
                  "name": "hooks",
                  "path": "app/frontend/src/hooks",
                  "type": "dir",
                  "size": null,
                  "children": [
                    {
                      "name": "useBranchDiff.ts",
                      "path": "app/frontend/src/hooks/useBranchDiff.ts",
                      "type": "file",
                      "size": 1354,
                      "children": null
                    },
                    {
                      "name": "useFileContent.ts",
                      "path": "app/frontend/src/hooks/useFileContent.ts",
                      "type": "file",
                      "size": 4635,
                      "children": null
                    },
                    {
                      "name": "useFileTree.ts",
                      "path": "app/frontend/src/hooks/useFileTree.ts",
                      "type": "file",
                      "size": 1124,
                      "children": null
                    },
                    {
                      "name": "useHighlightedDiff.ts",
                      "path": "app/frontend/src/hooks/useHighlightedDiff.ts",
                      "type": "file",
                      "size": 3638,
                      "children": null
                    },
                    {
                      "name": "useHighlightedFile.ts",
                      "path": "app/frontend/src/hooks/useHighlightedFile.ts",
                      "type": "file",
                      "size": 2201,
                      "children": null
                    },
                    {
                      "name": "useStackDetail.ts",
                      "path": "app/frontend/src/hooks/useStackDetail.ts",
                      "type": "file",
                      "size": 3276,
                      "children": null
                    }
                  ]
                },
                {
                  "name": "index.css",
                  "path": "app/frontend/src/index.css",
                  "type": "file",
                  "size": 1153,
                  "children": null
                },
                {
                  "name": "lib",
                  "path": "app/frontend/src/lib",
                  "type": "dir",
                  "size": null,
                  "children": [
                    {
                      "name": "file-icons",
                      "path": "app/frontend/src/lib/file-icons",
                      "type": "dir",
                      "size": null,
                      "children": [
                        {
                          "name": "index.ts",
                          "path": "app/frontend/src/lib/file-icons/index.ts",
                          "type": "file",
                          "size": 2264,
                          "children": null
                        },
                        {
                          "name": "packs",
                          "path": "app/frontend/src/lib/file-icons/packs",
                          "type": "dir",
                          "size": null,
                          "children": [
                            {
                              "name": "material.ts",
                              "path": "app/frontend/src/lib/file-icons/packs/material.ts",
                              "type": "file",
                              "size": 2172,
                              "children": null
                            }
                          ]
                        },
                        {
                          "name": "resolve.ts",
                          "path": "app/frontend/src/lib/file-icons/resolve.ts",
                          "type": "file",
                          "size": 4702,
                          "children": null
                        },
                        {
                          "name": "types.ts",
                          "path": "app/frontend/src/lib/file-icons/types.ts",
                          "type": "file",
                          "size": 3477,
                          "children": null
                        }
                      ]
                    },
                    {
                      "name": "lang-from-path.ts",
                      "path": "app/frontend/src/lib/lang-from-path.ts",
                      "type": "file",
                      "size": 1655,
                      "children": null
                    },
                    {
                      "name": "mock-data.ts",
                      "path": "app/frontend/src/lib/mock-data.ts",
                      "type": "file",
                      "size": 520,
                      "children": null
                    },
                    {
                      "name": "mock-diff-data.ts",
                      "path": "app/frontend/src/lib/mock-diff-data.ts",
                      "type": "file",
                      "size": 4249,
                      "children": null
                    },
                    {
                      "name": "mock-file-data.ts",
                      "path": "app/frontend/src/lib/mock-file-data.ts",
                      "type": "file",
                      "size": 564,
                      "children": null
                    },
                    {
                      "name": "shiki.ts",
                      "path": "app/frontend/src/lib/shiki.ts",
                      "type": "file",
                      "size": 951,
                      "children": null
                    },
                    {
                      "name": "utils.ts",
                      "path": "app/frontend/src/lib/utils.ts",
                      "type": "file",
                      "size": 1969,
                      "children": null
                    }
                  ]
                },
                {
                  "name": "main.tsx",
                  "path": "app/frontend/src/main.tsx",
                  "type": "file",
                  "size": 1619,
                  "children": null
                },
                {
                  "name": "types",
                  "path": "app/frontend/src/types",
                  "type": "dir",
                  "size": null,
                  "children": [
                    {
                      "name": "diff.ts",
                      "path": "app/frontend/src/types/diff.ts",
                      "type": "file",
                      "size": 5099,
                      "children": null
                    },
                    {
                      "name": "file-tree.ts",
                      "path": "app/frontend/src/types/file-tree.ts",
                      "type": "file",
                      "size": 269,
                      "children": null
                    },
                    {
                      "name": "stack.ts",
                      "path": "app/frontend/src/types/stack.ts",
                      "type": "file",
                      "size": 1610,
                      "children": null
                    }
                  ]
                }
              ]
            },
            {
              "name": "tsconfig.json",
              "path": "app/frontend/tsconfig.json",
              "type": "file",
              "size": 4909,
              "children": null
            },
            {
              "name": "vite-env.d.ts",
              "path": "app/frontend/vite-env.d.ts",
              "type": "file",
              "size": 4582,
              "children": null
            },
            {
              "name": "vite.config.ts",
              "path": "app/frontend/vite.config.ts",
              "type": "file",
              "size": 4764,
              "children": null
            }
          ]
        }
      ]
    },
    {
      "name": "docker-compose.yml",
      "path": "docker-compose.yml",
      "type": "file",
      "size": 297,
      "children": null
    },
    {
      "name": "docs",
      "path": "docs",
      "type": "dir",
      "size": null,
      "children": [
        {
          "name": "adrs",
          "path": "docs/adrs",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "001-cli-framework.md",
              "path": "docs/adrs/001-cli-framework.md",
              "type": "file",
              "size": 4119,
              "children": null
            },
            {
              "name": "002-backend-language.md",
              "path": "docs/adrs/002-backend-language.md",
              "type": "file",
              "size": 593,
              "children": null
            },
            {
              "name": "003-agentic-patterns-extraction.md",
              "path": "docs/adrs/003-agentic-patterns-extraction.md",
              "type": "file",
              "size": 3467,
              "children": null
            },
            {
              "name": "004-stack-branch-domain-model.md",
              "path": "docs/adrs/004-stack-branch-domain-model.md",
              "type": "file",
              "size": 1909,
              "children": null
            },
            {
              "name": "_template.md",
              "path": "docs/adrs/_template.md",
              "type": "file",
              "size": 2803,
              "children": null
            }
          ]
        },
        {
          "name": "epics",
          "path": "docs/epics",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "_template.md",
              "path": "docs/epics/_template.md",
              "type": "file",
              "size": 2587,
              "children": null
            },
            {
              "name": "ep-001-backend-mvp.md",
              "path": "docs/epics/ep-001-backend-mvp.md",
              "type": "file",
              "size": 2896,
              "children": null
            },
            {
              "name": "ep-001-orchestration-plan.md",
              "path": "docs/epics/ep-001-orchestration-plan.md",
              "type": "file",
              "size": 2959,
              "children": null
            },
            {
              "name": "ep-002-cli-chat-agent-runtime.md",
              "path": "docs/epics/ep-002-cli-chat-agent-runtime.md",
              "type": "file",
              "size": 1869,
              "children": null
            },
            {
              "name": "ep-003-stack-branch-pr-domain.md",
              "path": "docs/epics/ep-003-stack-branch-pr-domain.md",
              "type": "file",
              "size": 4838,
              "children": null
            },
            {
              "name": "ep-005-project-domain.md",
              "path": "docs/epics/ep-005-project-domain.md",
              "type": "file",
              "size": 2520,
              "children": null
            },
            {
              "name": "ep-006-frontend-mvp.md",
              "path": "docs/epics/ep-006-frontend-mvp.md",
              "type": "file",
              "size": 4853,
              "children": null
            }
          ]
        },
        {
          "name": "issues",
          "path": "docs/issues",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "_template.md",
              "path": "docs/issues/_template.md",
              "type": "file",
              "size": 1825,
              "children": null
            },
            {
              "name": "sb-001-bootstrap.md",
              "path": "docs/issues/sb-001-bootstrap.md",
              "type": "file",
              "size": 4298,
              "children": null
            },
            {
              "name": "sb-002-conversation-models.md",
              "path": "docs/issues/sb-002-conversation-models.md",
              "type": "file",
              "size": 2268,
              "children": null
            },
            {
              "name": "sb-003-agent-models.md",
              "path": "docs/issues/sb-003-agent-models.md",
              "type": "file",
              "size": 4112,
              "children": null
            },
            {
              "name": "sb-004-execution-models.md",
              "path": "docs/issues/sb-004-execution-models.md",
              "type": "file",
              "size": 1143,
              "children": null
            },
            {
              "name": "sb-005-conversation-molecule.md",
              "path": "docs/issues/sb-005-conversation-molecule.md",
              "type": "file",
              "size": 3532,
              "children": null
            },
            {
              "name": "sb-006-rest-api.md",
              "path": "docs/issues/sb-006-rest-api.md",
              "type": "file",
              "size": 1635,
              "children": null
            },
            {
              "name": "sb-007-wire-and-run.md",
              "path": "docs/issues/sb-007-wire-and-run.md",
              "type": "file",
              "size": 2427,
              "children": null
            },
            {
              "name": "sb-008-conversation-runtime.md",
              "path": "docs/issues/sb-008-conversation-runtime.md",
              "type": "file",
              "size": 2805,
              "children": null
            },
            {
              "name": "sb-009-cli-chat-mode.md",
              "path": "docs/issues/sb-009-cli-chat-mode.md",
              "type": "file",
              "size": 393,
              "children": null
            },
            {
              "name": "sb-010-wire-cli-to-backend.md",
              "path": "docs/issues/sb-010-wire-cli-to-backend.md",
              "type": "file",
              "size": 2394,
              "children": null
            },
            {
              "name": "sb-011-runtime-manager.md",
              "path": "docs/issues/sb-011-runtime-manager.md",
              "type": "file",
              "size": 360,
              "children": null
            },
            {
              "name": "sb-012-conversation-recall.md",
              "path": "docs/issues/sb-012-conversation-recall.md",
              "type": "file",
              "size": 1059,
              "children": null
            },
            {
              "name": "sb-013-streaming-markdown-renderer.md",
              "path": "docs/issues/sb-013-streaming-markdown-renderer.md",
              "type": "file",
              "size": 548,
              "children": null
            },
            {
              "name": "sb-035-frontend-scaffold.md",
              "path": "docs/issues/sb-035-frontend-scaffold.md",
              "type": "file",
              "size": 1829,
              "children": null
            },
            {
              "name": "sb-036-shared-atoms.md",
              "path": "docs/issues/sb-036-shared-atoms.md",
              "type": "file",
              "size": 587,
              "children": null
            },
            {
              "name": "sb-037-stack-navigation.md",
              "path": "docs/issues/sb-037-stack-navigation.md",
              "type": "file",
              "size": 1328,
              "children": null
            },
            {
              "name": "sb-038-app-shell.md",
              "path": "docs/issues/sb-038-app-shell.md",
              "type": "file",
              "size": 556,
              "children": null
            },
            {
              "name": "sb-039-diff-review.md",
              "path": "docs/issues/sb-039-diff-review.md",
              "type": "file",
              "size": 1599,
              "children": null
            }
          ]
        },
        {
          "name": "specs",
          "path": "docs/specs",
          "type": "dir",
          "size": null,
          "children": [
            {
              "name": "2026-03-14-agent-node-extraction.md",
              "path": "docs/specs/2026-03-14-agent-node-extraction.md",
              "type": "file",
              "size": 4441,
              "children": null
            },
            {
              "name": "2026-03-19-project-workspace-domain.md",
              "path": "docs/specs/2026-03-19-project-workspace-domain.md",
              "type": "file",
              "size": 4961,
              "children": null
            },
            {
              "name": "2026-03-19-stack-branch-pr-domain.md",
              "path": "docs/specs/2026-03-19-stack-branch-pr-domain.md",
              "type": "file",
              "size": 5091,
              "children": null
            },
            {
              "name": "_template.md",
              "path": "docs/specs/_template.md",
              "type": "file",
              "size": 5023,
              "children": null
            }
          ]
        }
      ]
    },
    {
      "name": "patterns.yaml",
      "path": "patterns.yaml",
      "type": "file",
      "size": 3311,
      "children": null
    },
    {
      "name": ".env",
      "path": ".env",
      "type": "file",
      "size": 500,
      "children": null
    }
  ]
};

const mockFiles: Record<string, FileContent> = {
  "app/frontend/src/App.tsx": {
    path: "app/frontend/src/App.tsx",
    content: `import { useState, useEffect, useMemo } from "react";
import { AppShell } from "@/components/templates";
import { FilesChangedPanel } from "@/components/organisms/FilesChangedPanel";
import { FileContent } from "@/components/molecules/FileContent";
import { PathBar } from "@/components/molecules/PathBar";
import { useStackDetail } from "@/hooks/useStackDetail";
import { useBranchDiff } from "@/hooks/useBranchDiff";
import { useFileTree } from "@/hooks/useFileTree";
import { useFileContent } from "@/hooks/useFileContent";
import { mockActivityEntries } from "@/lib/mock-activity-data";
import type { StackConnectorItem } from "@/components/molecules";
import type { DiffFileListItem } from "@/components/molecules/DiffFileList";
import type { ChangedFileInfo } from "@/components/organisms/FileTree";
import type { SidebarMode } from "@/types/sidebar";
import type { CIStatus, StackSummary, ActivityLogEntry } from "@/types/activity";

function branchTitle(name: string): string {
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}

export function App() {
  const { data, loading, error } = useStackDetail();
  const [activeIndex, setActiveIndex] = useState(2);
  const [sidebarMode, setSidebarMode] = useState<SidebarMode>("diffs");
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  // ...
}`,
    size: 5200,
    language: "tsx",
    lines: 211,
    truncated: false,
  },

  "app/frontend/src/components/atoms/Badge/Badge.tsx": {
    path: "app/frontend/src/components/atoms/Badge/Badge.tsx",
    content: `import { forwardRef, type HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full font-medium leading-none whitespace-nowrap",
  {
    variants: {
      size: {
        sm: "px-1.5 py-0.5 text-[10px]",
        default: "px-2 py-0.5 text-xs",
      },
      color: {
        default:
          "bg-[var(--bg-surface-hover)] text-[var(--fg-muted)] border border-[var(--border-muted)]",
        green:
          "bg-[var(--green-bg)] text-[var(--green)] border border-[var(--green)]/20",
        red:
          "bg-[var(--red-bg)] text-[var(--red)] border border-[var(--red)]/20",
        purple:
          "bg-[var(--purple)]/10 text-[var(--purple)] border border-[var(--purple)]/20",
        yellow:
          "bg-[var(--yellow)]/10 text-[var(--yellow)] border border-[var(--yellow)]/20",
        accent:
          "bg-[var(--accent-muted)] text-[var(--accent)] border border-[var(--accent)]/20",
      },
    },
    defaultVariants: {
      size: "default",
      color: "default",
    },
  }
);

type BadgeVariants = VariantProps<typeof badgeVariants>;

interface BadgeProps
  extends Omit<HTMLAttributes<HTMLSpanElement>, "color">,
    BadgeVariants {}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, size, color, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(badgeVariants({ size, color }), className)}
      {...props}
    />
  )
);

Badge.displayName = "Badge";

export { Badge, badgeVariants };
export type { BadgeProps };`,
    size: 1800,
    language: "tsx",
    lines: 55,
    truncated: false,
  },

  "app/frontend/src/components/atoms/DiffStat/DiffStat.tsx": {
    path: "app/frontend/src/components/atoms/DiffStat/DiffStat.tsx",
    content: `interface DiffStatProps {
  additions: number;
  deletions: number;
}

function DiffStat({ additions, deletions }: DiffStatProps) {
  if (additions === 0 && deletions === 0) {
    return null;
  }

  return (
    <span className="inline-flex items-center gap-0.5 font-[family-name:var(--font-mono)] text-xs tabular-nums">
      <span className="text-[var(--green)] w-8 text-right">+{additions}</span>
      <span className="text-[var(--red)] w-8 text-right">-{deletions}</span>
    </span>
  );
}

DiffStat.displayName = "DiffStat";

export { DiffStat };
export type { DiffStatProps };`,
    size: 580,
    language: "tsx",
    lines: 23,
    truncated: false,
  },

  "app/frontend/src/components/atoms/StackDot/StackDot.tsx": {
    path: "app/frontend/src/components/atoms/StackDot/StackDot.tsx",
    content: `import { cn } from "@/lib/utils";

type StackDotColor = "default" | "accent" | "green";

interface StackDotProps {
  color?: StackDotColor;
  isFirst?: boolean;
  isLast?: boolean;
}

const dotColorMap: Record<StackDotColor, string> = {
  default: "bg-[var(--fg-subtle)]",
  accent: "bg-[var(--accent)]",
  green: "bg-[var(--green)]",
};

const lineColorMap: Record<StackDotColor, string> = {
  default: "bg-[var(--border)]",
  accent: "bg-[var(--border)]",
  green: "bg-[var(--border)]",
};

function StackDot({ color = "default", isFirst = false, isLast = false }: StackDotProps) {
  return (
    <div className="relative flex flex-col items-center w-4 self-stretch">
      <div
        className={cn(
          "w-px flex-1",
          isFirst ? "bg-transparent" : lineColorMap[color]
        )}
      />
      <div
        className={cn(
          "w-2.5 h-2.5 rounded-full shrink-0 ring-2 ring-[var(--bg-surface)]",
          dotColorMap[color]
        )}
      />
      <div
        className={cn(
          "w-px flex-1",
          isLast ? "bg-transparent" : lineColorMap[color]
        )}
      />
    </div>
  );
}

StackDot.displayName = "StackDot";

export { StackDot };
export type { StackDotProps, StackDotColor };`,
    size: 1400,
    language: "tsx",
    lines: 55,
    truncated: false,
  },

  "app/frontend/src/components/molecules/StackItem/StackItem.tsx": {
    path: "app/frontend/src/components/molecules/StackItem/StackItem.tsx",
    content: `import { cn } from "@/lib/utils";
import { StackDot, DiffStat, CIDot, PRNumber, RestackBadge } from "@/components/atoms";
import type { StackDotColor } from "@/components/atoms";
import { StatusBadge } from "@/components/molecules/StatusBadge";
import type { CIStatus } from "@/types/activity";

interface StackItemProps {
  title: string;
  status: string;
  additions?: number;
  deletions?: number;
  prNumber?: number | null;
  ciStatus?: CIStatus;
  needsRestack?: boolean;
  isActive?: boolean;
  isFirst?: boolean;
  isLast?: boolean;
  onClick?: () => void;
}

function getStackDotColor(status: string, isActive: boolean): StackDotColor {
  if (status === "merged") return "green";
  if (isActive) return "accent";
  return "default";
}

function StackItem({
  title,
  status,
  additions = 0,
  deletions = 0,
  prNumber,
  ciStatus,
  needsRestack,
  isActive = false,
  isFirst = false,
  isLast = false,
  onClick,
}: StackItemProps) {
  const dotColor = getStackDotColor(status, isActive);

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-stretch gap-2 w-full px-3 py-1.5 text-left transition-colors rounded-md",
        isActive
          ? "bg-[var(--accent-muted)] text-[var(--accent)]"
          : "text-[var(--fg-default)] hover:bg-[var(--bg-surface-hover)]"
      )}
    >
      <StackDot color={dotColor} isFirst={isFirst} isLast={isLast} />
      <div className="flex flex-col gap-0.5 min-w-0 flex-1">
        <span
          className={cn(
            "text-[13px] font-medium truncate",
            isActive ? "text-[var(--accent)]" : "text-[var(--fg-default)]"
          )}
        >
          {title}
        </span>
        <div className="flex items-center gap-1.5">
          <StatusBadge status={status} />
          {prNumber != null && prNumber > 0 && <PRNumber number={prNumber} />}
          <CIDot status={ciStatus ?? "none"} />
          {needsRestack && <RestackBadge />}
          {(additions > 0 || deletions > 0) && (
            <span className="ml-auto">
              <DiffStat additions={additions} deletions={deletions} />
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

StackItem.displayName = "StackItem";

export { StackItem };
export type { StackItemProps };`,
    size: 2200,
    language: "tsx",
    lines: 83,
    truncated: false,
  },

  "app/frontend/src/components/molecules/StatusBadge/StatusBadge.tsx": {
    path: "app/frontend/src/components/molecules/StatusBadge/StatusBadge.tsx",
    content: `import { Badge } from "@/components/atoms";
import type { BadgeProps } from "@/components/atoms";

type StatusString =
  | "draft"
  | "created"
  | "pushed"
  | "local"
  | "open"
  | "reviewing"
  | "review"
  | "approved"
  | "ready"
  | "submitted"
  | "merged"
  | "closed"
  | "active";

const statusColorMap: Record<StatusString, BadgeProps["color"]> = {
  draft: "default",
  created: "default",
  pushed: "default",
  local: "default",
  active: "accent",
  open: "accent",
  reviewing: "accent",
  review: "purple",
  approved: "purple",
  ready: "purple",
  submitted: "yellow",
  merged: "green",
  closed: "red",
};

const statusLabelMap: Record<StatusString, string> = {
  draft: "Draft",
  created: "Local",
  pushed: "Pushed",
  local: "Local",
  active: "Active",
  open: "Open",
  reviewing: "Reviewing",
  review: "Review",
  approved: "Approved",
  ready: "Ready",
  submitted: "Submitted",
  merged: "Merged",
  closed: "Closed",
};

interface StatusBadgeProps {
  status: string;
}

function StatusBadge({ status }: StatusBadgeProps) {
  const key = status as StatusString;
  const color = statusColorMap[key] ?? "default";
  const label = statusLabelMap[key] ?? status;

  return (
    <Badge size="sm" color={color}>
      {label}
    </Badge>
  );
}

StatusBadge.displayName = "StatusBadge";

export { StatusBadge };
export type { StatusBadgeProps, StatusString };`,
    size: 1800,
    language: "tsx",
    lines: 71,
    truncated: false,
  },

  "app/frontend/src/hooks/useStackDetail.ts": {
    path: "app/frontend/src/hooks/useStackDetail.ts",
    content: `import { useState } from "react";
import type { StackDetail } from "@/types/stack";
import { mockStackDetail } from "@/lib/mock-data";

interface UseStackDetailResult {
  data: StackDetail | null;
  loading: boolean;
  error: string | null;
}

export function useStackDetail(_stackId?: string): UseStackDetailResult {
  // MVP: return mock data directly. Replace with real fetch when backend is wired.
  const [data] = useState<StackDetail | null>(mockStackDetail);
  const [loading] = useState(false);
  const [error] = useState<string | null>(null);

  return { data, loading, error };
}`,
    size: 520,
    language: "typescript",
    lines: 19,
    truncated: false,
  },

  "app/frontend/src/hooks/useBranchDiff.ts": {
    path: "app/frontend/src/hooks/useBranchDiff.ts",
    content: `import { useState } from "react";
import type { DiffData } from "@/types/diff";
import { mockDiffDataByBranch } from "@/lib/mock-diff-data";

interface UseBranchDiffResult {
  data: DiffData | null;
  loading: boolean;
  error: string | null;
}

export function useBranchDiff(branchId: string | undefined): UseBranchDiffResult {
  // MVP: return mock data directly. Replace with real fetch when backend is wired.
  const [loading] = useState(false);
  const [error] = useState<string | null>(null);

  const data = branchId ? (mockDiffDataByBranch[branchId] ?? null) : null;

  return { data, loading, error };
}`,
    size: 540,
    language: "typescript",
    lines: 20,
    truncated: false,
  },

  "app/frontend/src/lib/utils.ts": {
    path: "app/frontend/src/lib/utils.ts",
    content: `import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}`,
    size: 120,
    language: "typescript",
    lines: 5,
    truncated: false,
  },

  "app/frontend/src/types/stack.ts": {
    path: "app/frontend/src/types/stack.ts",
    content: `export interface Stack {
  id: string;
  reference_number: string | null;
  project_id: string;
  name: string;
  base_branch_id: string | null;
  trunk: string;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface Branch {
  id: string;
  reference_number: string | null;
  stack_id: string;
  workspace_id: string;
  name: string;
  position: number;
  head_sha: string | null;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface PullRequest {
  id: string;
  reference_number: string | null;
  branch_id: string;
  external_id: number | null;
  external_url: string | null;
  title: string;
  description: string | null;
  review_notes: string | null;
  state: string;
  created_at: string;
  updated_at: string;
}

export interface BranchWithPR {
  branch: Branch;
  pull_request: PullRequest | null;
}

export interface StackDetail {
  stack: Stack;
  branches: BranchWithPR[];
}`,
    size: 820,
    language: "typescript",
    lines: 49,
    truncated: false,
  },

  "app/frontend/src/types/diff.ts": {
    path: "app/frontend/src/types/diff.ts",
    content: `export interface DiffLine {
  type: "context" | "add" | "del" | "hunk";
  old_num: number | null;
  new_num: number | null;
  content: string;
  highlightedHtml?: string;
}

export interface DiffHunk {
  header: string;
  lines: DiffLine[];
}

export interface DiffFile {
  path: string;
  change_type: "added" | "modified" | "deleted" | "renamed";
  additions: number;
  deletions: number;
  hunks: DiffHunk[];
}

export interface DiffData {
  files: DiffFile[];
  total_additions: number;
  total_deletions: number;
}`,
    size: 520,
    language: "typescript",
    lines: 27,
    truncated: false,
  },

  "app/frontend/src/index.css": {
    path: "app/frontend/src/index.css",
    content: `@import "tailwindcss";

/*
 * Stack Bench -- Dark Design System Tokens
 *
 * All colors, fonts, and semantic values are defined here as CSS custom
 * properties. Components reference these via var(--token-name). Never
 * hardcode color values in component code.
 */

:root {
  --bg-canvas: #0d1117;
  --bg-surface: #161b22;
  --bg-surface-hover: #1c2128;
  --bg-inset: #010409;

  --border: #30363d;
  --border-muted: #21262d;

  --fg-default: #e6edf3;
  --fg-muted: #7d8590;
  --fg-subtle: #484f58;

  --accent: #58a6ff;
  --green: #3fb950;
  --red: #f85149;
  --purple: #bc8cff;
  --yellow: #d29922;

  --accent-emerald: #6ee7b7;
  --accent-emerald-dim: #065f46;

  --green-bg: #12261e;
  --red-bg: #28171a;
}

body {
  margin: 0;
  background-color: var(--bg-canvas);
  color: var(--fg-default);
  font-family: system-ui, sans-serif;
}`,
    size: 780,
    language: "css",
    lines: 44,
    truncated: false,
  },

  "app/frontend/src/main.tsx": {
    path: "app/frontend/src/main.tsx",
    content: `import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);`,
    size: 240,
    language: "tsx",
    lines: 10,
    truncated: false,
  },

  "app/frontend/package.json": {
    path: "app/frontend/package.json",
    content: `{
  "name": "@stack-bench/frontend",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@radix-ui/react-collapsible": "^1.1.12",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "shiki": "^4.0.2"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0"
  }
}`,
    size: 640,
    language: "json",
    lines: 29,
    truncated: false,
  },

  "app/frontend/tsconfig.json": {
    path: "app/frontend/tsconfig.json",
    content: `{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src", "vite-env.d.ts"],
  "exclude": ["src/generated"]
}`,
    size: 560,
    language: "json",
    lines: 27,
    truncated: false,
  },

  "CLAUDE.md": {
    path: "CLAUDE.md",
    content: `# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Stack Bench is a developer workbench for AI-assisted development with stacked PRs.
It combines a Go CLI (TUI), a Python backend (pattern-stack + agentic-patterns),
and a React frontend.

## Repository Layout

app/
  backend/              # Python backend (self-contained service)
  cli/                  # Go CLI (Bubble Tea TUI)
  frontend/             # React frontend
docs/
  adrs/                 # Architecture Decision Records
  specs/                # Implementation specs
  epics/                # Groups of related issues (EP-NNN)
  issues/               # Individual work units (SB-NNN)`,
    size: 620,
    language: "markdown",
    lines: 22,
    truncated: true,
  },
};

export function getMockFileContent(path: string): FileContent | null {
  return mockFiles[path] ?? null;
}
