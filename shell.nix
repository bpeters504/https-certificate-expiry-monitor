with import <nixpkgs> {};
mkShell {
  buildInputs = [
    python312
    python312Packages.flask
    python312Packages.waitress
    python312Packages.configparser
  ];
}
