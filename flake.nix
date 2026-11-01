# agentic-nomad toolkit — adapted from the nix-dev-toolkit template (kattakath/skills).
#
#   nix develop          → uv/uvx, node/npx, python3, jq, gh
#   nix fmt              → treefmt (nixfmt + ruff-format)
#   nix flake check      → formatting + toolchain-complete + project-gate (hook tests, OFFLINE)
#                          + every package (writeShellApplication shellchecks it at build)
#   nix run .#env-doctor → which catalogued secrets are set (NAMES only, never values)
#
# Dropped from the template on purpose: the Postgres stack and runner provisioning. Records
# live in Google (ADR-0002); this repo holds rules, skills and hooks only.
{
  description = "agentic-nomad — a Claude Code travel agent that runs unattended up to the payment page";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      treefmt-nix,
    }:
    let
      # x86_64-darwin is absent on purpose: nixpkgs-unstable throws on it.
      systems = [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f system nixpkgs.legacyPackages.${system});
      inherit (nixpkgs) lib;

      treefmtEval = forAll (_: pkgs: treefmt-nix.lib.evalModule pkgs ./treefmt.nix);

      # ── Env catalogue: the single source of truth for every operator-set variable .mcp.json and
      # the hooks read. `.env.example` mirrors it; `env-doctor` reports presence only. Left out on
      # purpose: CLAUDE_PROJECT_DIR (set by Claude Code) and NOMAD_STATE_DIR (a test-only override
      # of page_scope.py's state directory).
      envCatalogue = {
        LITEAPI_API_KEY = {
          need = "optional";
          secret = true;
          note = "LiteAPI SANDBOX key (keys are environment-specific): rates search.";
        };
        DUFFEL_ACCESS_TOKEN = {
          need = "optional";
          secret = true;
          note = "Duffel duffel_test_ token, for the unbuilt fallback rail (ADR-0001). Use test tokens only; nothing checks the prefix any more.";
        };
        BLAND_API_KEY = {
          need = "optional";
          secret = true;
          note = "Bland voice MCP, for later; the server is disabled in settings.json.";
        };
        NOMAD_ALLOW_LIVE = {
          need = "optional";
          secret = false;
          note = "No effect since the spend guard was removed (2026-10-27); kept so .env.example stays in sync.";
        };
      };
      envNames = lib.attrNames envCatalogue;
      envTsv = lib.concatMapStringsSep "\n" (
        n:
        let
          e = envCatalogue.${n};
        in
        lib.concatStringsSep "\t" [
          n
          e.need
          (if e.secret then "secret" else "plain")
          e.note
        ]
      ) envNames;

      # ONE list read by devShells AND toolchain-complete, so they cannot drift.
      devPackagesFor =
        pkgs: with pkgs; [
          uv
          nodejs_22
          python3
          jq
          gh
          git
        ];
      # Binaries .mcp.json, the hook and the skills shell out to. A package name is not a binary
      # name (uv ships uvx; nodejs_22 ships npx) — that map is what this check guards.
      requiredBins = [
        "uv"
        "uvx"
        "node"
        "npx"
        "python3"
        "jq"
        "gh"
        "git"
      ];

      # The real gate, offline: stdlib-only hook tests. Two commands, NOT `a && b`: under the
      # builder's `set -e` a failing `a` in an && list does not stop the script, so the gate
      # went green with a failing unittest (measured 2026-11-01).
      projectGate = {
        command = "python3 -m unittest discover -s .claude/hooks/tests -v\nnode --test .claude/tools/tests/*.test.mjs";
        packages = p: [
          p.python3
          p.nodejs_22
        ];
      };
    in
    {
      formatter = forAll (system: _: treefmtEval.${system}.config.build.wrapper);

      packages = forAll (
        _system: pkgs:
        let
          envTsvFile = pkgs.writeText "agentic-nomad-env-catalogue.tsv" envTsv;
        in
        {
          env-doctor = pkgs.writeShellApplication {
            name = "env-doctor";
            text = ''
              # PRESENCE ONLY. Never prints a value.
              printf '%-22s %-9s %-7s %s\n' VARIABLE NEED KIND STATUS
              while IFS=$'\t' read -r n need kind _note; do
                [ -z "$n" ] && continue
                if [ -n "''${!n:-}" ]; then st="set"; else st="MISSING"; fi
                printf '%-22s %-9s %-7s %s\n' "$n" "$need" "$kind" "$st"
              done < ${envTsvFile}
            '';
          };
        }
      );

      apps = forAll (
        system: _:
        lib.mapAttrs (name: drv: {
          type = "app";
          program = "${drv}/bin/${name}";
          meta.description = "agentic-nomad ${name}";
        }) self.packages.${system}
      );

      devShells = forAll (
        _system: pkgs: {
          default = pkgs.mkShell {
            packages = devPackagesFor pkgs;
            shellHook = ''
              echo "agentic-nomad — ${toString (builtins.length envNames)} catalogued vars; nix run .#env-doctor"
            '';
          };
        }
      );

      checks = forAll (
        system: pkgs:
        let
          gateSrc = lib.fileset.toSource {
            root = ./.;
            fileset = lib.fileset.unions [
              ./.claude
              ./.mcp.json
            ];
          };
        in
        self.packages.${system}
        // {
          formatting = treefmtEval.${system}.config.build.check self;

          toolchain-complete =
            pkgs.runCommandLocal "toolchain-complete" { nativeBuildInputs = devPackagesFor pkgs; }
              ''
                missing=""
                for bin in ${lib.escapeShellArgs requiredBins}; do
                  command -v "$bin" >/dev/null 2>&1 || missing="$missing $bin"
                done
                if [ -n "$missing" ]; then
                  echo "dev shell is missing:$missing" >&2
                  exit 1
                fi
                echo "all ${toString (builtins.length requiredBins)} required binaries resolve." > "$out"
              '';

          project-gate =
            pkgs.runCommandLocal "project-gate" { nativeBuildInputs = projectGate.packages pkgs; }
              ''
                mkdir gate
                cp -R ${gateSrc}/. gate/
                chmod -R u+w gate
                cd gate
                ${projectGate.command}
                touch "$out"
              '';
        }
      );
    };
}
