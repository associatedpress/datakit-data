class ExtraFlags:
    """
    API for converting datakit-layer CLI flags for pass-through to AWS
    command-line utilities such as 'S3 sync' command.
    """

    @classmethod
    def convert(kls, raw_flags):
        """
        :param raw_flags: Array of boolean command-line flags
        """
        return ["--{}".format(flag) for flag in raw_flags]
