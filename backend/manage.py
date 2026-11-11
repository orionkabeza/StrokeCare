#!/usr/bin/env python
# Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "strokecare.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
