# Developer notes

## How to setup python environment for mypy and pytest

```bash
cd software
python -m venv test-venv
. test-venv/bin/activate
pip install -r tests/requirements.txt
pip install -U micropython-rp2-pico_w-stubs --target typings
```


## 'database' schema for btree db

### Playlist storage

The playlist data is stored in the btree database in a hierarchical schema. The hierarchy levels are
separated by the '/' character.  Currently, the schema is as follows: The top level for a playlist
is the 'tag' id encoded as a hexadecimal string. Beneath this, the 'playlist' key contains the
elements in the playlist. The keys used for the playlist entries must be decimal integers,
left-padded with zeros so their length is 5 (e.g. format `{:05}`).

#### Playlist modes

The 'playlistshuffle' key located under the 'tag' key can be 'no' or 'yes' and specifies whether the
playlist is in shuffle mode. Should this key be absent the default value is 'no'.

The 'playlistpersist' key located under the 'tag' key can be 'no', 'track' or 'offset'. Should this
key be absent the default value is 'track'.

 * When it is 'no', the playlist position is not saved when playback stops. If shuffle mode is
   active, the shuffle random seed is also not saved.
 * When it is 'track', the currently playing track is saved when playback stops. If shuffle mode is
   active, the shuffle random seed is also saved. Should playback reach the last track (in shuffle
   mode: the last track in the permutated order), the saved position is reset and playback is
   stopped. The next time the playlist is started it will start from the first track and with a new
   shuffle seed if applicable.
 * When it is 'offset', the operation is basically the same as in 'track' mode. The difference is
   that the offset in the currently playing track is also saved and playback will resume at that
   position.

The 'playlistpos' key located under the 'tag' key stores the key of the current playlist
entry. The 'playlistshuffleseed' key stores the random seed used to shuffle the playlist.
The 'playlistposoffset' key stores the offset in the current playlist entry.

#### Example

For example, a playlist with two entries 'a.mp3' and 'b.mp3' for a tag with the id '00aa11bb22'
would be stored in the following key/value pairs in the btree db:

 * 00aa11bb22/playlist/00000: a.mp3
 * 00aa11bb22/playlist/00001: b.mp3
 * 00aa11bb22/playlistpos: 00000

## Notes for UI development with chromium

Features for the web interface are best prototyped in a browser directly. By using the built-in developmer tools and
and their "override" feature, the web contents are replaced by a locally stored copy, which can be used to directly
test the modifications without going all the way through the build and flash process.

However, modern browsers may restrict or even completely forbid the execution of dynamic content like JavaScript, if
the content is stored on the local machine and/or the content is accessed using http. In such a case, chromium issues
an error message similar to the following one:

> Access to fetch at 'http://192.168.4.1/api/v1/audiofiles' from origin 'http://192.168.4.1' has been blocked by CORS
> policy: The request client is not a secure context and the resource is in more-private address space `local`.

To mitigate this, chromium offers two flags that need modification:
- 'chrome://flags/#local-network-access-check' must be `Disabled`
- 'chrome://flags/#unsafely-treat-insecure-origin-as-secure' must be `Enabled`

Note that these settings leave the browser susceptible to security issues and should be returned to
their default values as soon as possible.
