with import <nixpkgs> {};
mkShell {
  buildInputs = [
    python312
    python312Packages.flask
    python312Packages.waitress
    python312Packages.configparser
  ];

  shellHook = ''
    export PS1='\n\[\033[1;91m\][nix-shell:\[\033[1;32m\]\w]\$\[\033[0m\] '
  '';

}
