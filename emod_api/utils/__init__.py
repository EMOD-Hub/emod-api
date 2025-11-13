from collections.abc import Iterable


def check_dimensionality(data, dimensionality: int) -> bool:
    """
    Returns True/False: is the provided data a matrix of the specified dimensionality?
    Args:
        data: An object to check the dimensionality of
        dimensionality: The expected dimensionality

    Returns:
        True if data dimensionality is as expected, False if not.
    """
    ret = True
    if dimensionality == 0:
        if isinstance(data, Iterable):
            ret = False  # expected to NOT be iterable still, but it is
    else:
        if isinstance(data, Iterable):
            for item in data:
                if check_dimensionality(data=item, dimensionality=dimensionality - 1) is False:
                    ret = False
                    break
        else:
            ret = False  # expected to be iterable still, but it isn't
    return ret
