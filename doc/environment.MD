# Environment Variabels

If you want to set environment variable (like set some path) in docker environment, you can do it in "hook_pre_useradd" by

`
  ENV path=/your/path
`

which equals to

`
  export path=/your/path
`
