"""Verified desktop update connections with both system and bundled trust roots."""
import ssl
import certifi


def update_ssl_context():
    # Keep Windows/organization roots and add the portable public CA bundle.
    # Never replace the system store or relax hostname/certificate verification.
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def update_error_message(error):
    reason = getattr(error, 'reason', error)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return ('This computer could not verify the update website\u2019s security certificate. '
                'Check this PC\u2019s date and time and install Windows updates. '
                'If it continues, ask your administrator to check the computer\u2019s '
                'trusted certificates and any network security filtering. '
                'No update was installed.')
    return str(error)
