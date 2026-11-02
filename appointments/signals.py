"""Signaux de l'application appointments."""

import logging

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Document

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=Document)
def delete_document_file(sender, instance, using, **kwargs):  # pylint: disable=unused-argument
    """Supprime le fichier du stockage (disque ou R2) quand un Document est supprimé.

    Déclenché quelle que soit l'origine de la suppression : admin, cascade
    depuis un rendez-vous ou code. La suppression du fichier n'a lieu qu'après
    la validation de la transaction (on_commit) : si la suppression en base est
    annulée, le fichier est conservé.
    """
    if not instance.file:
        return
    # Copie du stockage et du nom : l'instance n'existe plus en base au moment du commit
    storage = instance.file.storage
    name = instance.file.name

    def remove_file():
        """Supprime le fichier ; une erreur de stockage est journalisée, jamais propagée."""
        try:
            storage.delete(name)
        except Exception:  # pylint: disable=broad-exception-caught
            # Le document est déjà supprimé en base : on ne fait pas planter la requête
            logger.exception("Impossible de supprimer le fichier %s du stockage", name)

    transaction.on_commit(remove_file, using=using)
