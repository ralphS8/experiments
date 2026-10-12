# Experiments page

The camera canvas for the Experiments page on ralphsagrott.com. GitHub hosts it for free, and Cargo shows it through an iframe you paste into the page's HTML.

Once set up, the page lives at `https://YOUR-USERNAME.github.io/experiments/`.

```
index.html          the canvas
experiments.json    list of pieces (rebuilt automatically, don't edit)
media/              web-sized photos and videos (made automatically)
add-experiments/    drop new experiments here
scripts/            the program that prepares experiments
cargo-embed.html    the code to paste into Cargo
.github/workflows/  the automatic step that runs after every upload
```

---

## 1. Set up the repository (once, about 10 minutes)

1. **Make a GitHub account** at github.com if you don't have one.
2. **Create a repository:** click **+** (top right), then **New repository**.
   - Name: `experiments`. This becomes part of the page address. If you choose another name, change it in `cargo-embed.html` too.
   - Set it to **Public**. Free GitHub Pages needs a public repository.
   - Click **Create repository**.
3. **Upload these files:** on the new repository's page, click **uploading an existing file**.
   - Unzip this package and open the folder.
   - **Important:** press **Cmd + Shift + .** in Finder to show hidden files, so the `.github` folder uploads too.
   - Select everything inside the folder and drag it onto the GitHub page. Click **Commit changes**.
4. **Turn on GitHub Pages:** go to **Settings**, then **Pages** (left sidebar). Under **Build and deployment**, set **Source** to **GitHub Actions**.
5. **Run it once:** go to the **Actions** tab, click **Build and publish Experiments** on the left, then **Run workflow**. After a minute or two it shows a green tick.
6. **Check it:** open `https://YOUR-USERNAME.github.io/experiments/`. It says "No experiments yet" until you add some.

## 2. Add experiments

1. In the repository, open the **add-experiments** folder.
2. Click **Add file**, then **Upload files**, and drag your files in. Upload 4–5 videos at a time; the website uploader struggles with big batches.
3. Click **Commit changes**.
4. Watch the **Actions** tab. A run starts straight away and takes a few minutes per batch. When it shows a green tick, refresh the page.

**Name each file** `Year - Title - Medium`, for example `2025 - Sand Wave - Houdini.mp4`.
- Add ` - sound` to the end to keep a video's audio (`2023 - VOLVER - Motion - sound.mp4`). Without it, the audio is removed and no sound control is shown.
- For two mediums, join them with `_` (`Motion_Illustration` shows as "Motion / Illustration"). Avoid `/`, which a Mac saves as `:`.

What happens automatically:
- Videos are resized to 1280px on the long edge, compressed to roughly 1–12 MB, and given a still frame. Stills are resized to 2000px and compressed.
- The pieces appear on the canvas with their title, year and medium taken from the filename.
- The files you uploaded are cleared from `add-experiments/` so it's empty for next time.

Files over 25 MB can't be uploaded through the GitHub website. Re-export them smaller, or use the free GitHub Desktop app: clone the repository, copy the file into its `add-experiments` folder, then **Commit to main** and **Push origin**.

### Remove or rename a piece

- **Remove:** open `media/`, click the file, open the **⋯** menu (top right), choose **Delete file** and commit.
- **Rename** (fix a title, year or medium, or turn sound on or off): open the file in `media/`, use the **⋯** menu or pencil icon to rename it, and commit. The still frame is remade to match.

The page updates a minute or two after each change.

## 3. Add it to Cargo

1. Open `cargo-embed.html` in a text editor and replace `YOUR-USERNAME` with your GitHub username.
2. In Cargo, open the Experiments page, switch the editor to its HTML (code) view, and paste in the whole file.
3. Set the page's padding to 0 so the canvas fills the page area.

The file holds two parts:
- **The iframe**, which shows the canvas.
- **A style block**, which turns the background and sidebar text dark and adds the film grain across the whole screen while the Experiments page is open. (The canvas switches its own grain off when it's embedded, so there's one unbroken layer.) If you only want the canvas, delete everything from `<style>` to `</style>`.

**Check after pasting:** open Experiments, then go to another page. The site should go back to its normal look. If the dark styling stays, the style block needs scoping for your Cargo template.

### Optional

Add to the end of the iframe address:
- `?edge=none` turns off the focus blur where the canvas meets the sidebar.
- `?edge=left` or `?edge=top` fixes which side it's on. By default it's on the left on wide screens and along the top on narrow ones.

Typeface: the readouts use ABC Diatype Mono if it's installed or licensed for web, and Geist Mono otherwise.

## Troubleshooting

**Nothing happens after an upload.** The `.github` folder probably didn't upload (it's hidden on a Mac). In the repository click **Add file → Create new file**, type `.github/workflows/site.yml` as the name, paste in that file's contents from this package, and commit.

**The run fails at "Save processed files".** Go to **Settings → Actions → General → Workflow permissions**, choose **Read and write permissions**, save, and re-run the workflow from the Actions tab.

**A file was skipped.** The run shows a yellow warning naming it. Unprocessed files stay in `add-experiments/` so you can fix the name or format and upload again.

**The page hasn't changed.** Wait for the green tick in Actions, then refresh.
