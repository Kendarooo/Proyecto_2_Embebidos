require recipes-core/images/core-image-minimal.bb

SUMMARY = "Imagen DRC Assistant — Jetson Nano"

IMAGE_INSTALL:append = " \
    ollama \
    drc-assistant \
    docker \
    kernel-modules \
    openssh-sftp-server \
    openssh-sshd \
    openssh-ssh \
    curl \
    expand-rootfs \
    e2fsprogs-resize2fs \
    parted \
"

# Habilitar SSH en el arranque
EXTRA_IMAGE_FEATURES += "ssh-server-openssh debug-tweaks"

# Espacio mínimo para que la imagen flashee —
# expand-rootfs.service se encarga de usar toda la SD en el primer boot
IMAGE_ROOTFS_EXTRA_SPACE = "2000000"

DISTRO_FEATURES:append = " systemd"
VIRTUAL-RUNTIME_init_manager = "systemd"

disable_getty_tty1() {
    # Quitar getty de tty1 para que drc-assistant.service use esa consola
    rm -f ${IMAGE_ROOTFS}${systemd_system_unitdir}/getty.target.wants/getty@tty1.service
}
ROOTFS_POSTPROCESS_COMMAND += "disable_getty_tty1;"

# Permitir login SSH como root sin contraseña
configure_sshd() {
    mkdir -p ${IMAGE_ROOTFS}/etc/ssh
    cat > ${IMAGE_ROOTFS}/etc/ssh/sshd_config << 'EOF'
Port 22
PermitRootLogin yes
PasswordAuthentication yes
PermitEmptyPasswords yes
UsePAM no
PrintMotd no
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/openssh/sftp-server
EOF
}
ROOTFS_POSTPROCESS_COMMAND += "configure_sshd;"
