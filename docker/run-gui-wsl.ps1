param(
    [string]$Distro = "Ubuntu"
)

$ErrorActionPreference = "Stop"
$project = "/mnt/d/PercetptIA/Self_Balancing_Robot"

wsl -d $Distro -- bash -lc "cd $project && chmod +x docker/*.sh && ./docker/run-gui-linux.sh"