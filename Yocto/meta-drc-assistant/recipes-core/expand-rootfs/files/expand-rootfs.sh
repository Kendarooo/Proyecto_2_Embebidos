#!/bin/sh
# Expande la partición root para ocupar todo el espacio disponible en la SD/eMMC

DEVICE="/dev/mmcblk0"
PARTNUM="1"
PARTITION="${DEVICE}p${PARTNUM}"

echo "expand-rootfs: Expandiendo ${PARTITION}..."

# Obtener el sector de inicio de la partición
START=$(fdisk -l ${DEVICE} | grep "${PARTITION}" | awk '{print $2}')
if [ -z "$START" ]; then
    echo "expand-rootfs: ERROR — no se encontró la partición ${PARTITION}"
    exit 1
fi

# Recrear la partición usando todo el espacio restante
# Nota: la secuencia d/n/p/1/START/enter/w es:
#   d     = delete partition
#   n     = new partition
#   p     = primary
#   1     = partition number
#   START = mismo sector de inicio
#   enter = usar todo el espacio restante
#   w     = write
echo "d
n
p
${PARTNUM}
${START}

w" | fdisk ${DEVICE}

# Recargar tabla de particiones
partprobe ${DEVICE} 2>/dev/null || true

# Expandir el filesystem
resize2fs ${PARTITION}

echo "expand-rootfs: Expansión completada."
df -h ${PARTITION}
