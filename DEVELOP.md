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
elements in the playlist. The keys used for the playlist entries should be decimal integers,
prefixed with sufficient zeros such that they are in the correct order when sorted
lexicographically. All keys must have the same width. When writing a playlist using the playlistdb
module, the keys are 00000, 00001, etc. by default.

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
