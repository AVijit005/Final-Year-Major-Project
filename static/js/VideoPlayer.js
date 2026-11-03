const container = document.querySelector(".container");

if (container) {
    const mainVideo = container.querySelector("video");
    const videoTimeline = container.querySelector(".video-timeline");
    const progressBar = container.querySelector(".progress-bar");
    const volumeBtn = container.querySelector(".volume i");
    const volumeSlider = container.querySelector(".left input");
    const currentVidTime = container.querySelector(".current-time");
    const videoDuration = container.querySelector(".video-duration");
    const skipBackward = container.querySelector(".skip-backward i");
    const skipForward = container.querySelector(".skip-forward i");
    const playPauseBtn = container.querySelector(".play-pause i");
    const speedBtn = container.querySelector(".playback-speed span");
    const speedOptions = container.querySelector(".speed-options");
    const pipBtn = container.querySelector(".pic-in-pic span");
    const fullScreenBtn = container.querySelector(".fullscreen i");
    let timer;

    if (mainVideo) {
        const hideControls = () => {
            if (mainVideo.paused) return;
            timer = setTimeout(() => {
                container.classList.remove("show-controls");
            }, 3000);
        };
        hideControls();

        container.addEventListener("mousemove", () => {
            container.classList.add("show-controls");
            clearTimeout(timer);
            hideControls();
        });

        const formatTime = time => {
            if (isNaN(time) || time < 0) return "00:00";
            let seconds = Math.floor(time % 60),
                minutes = Math.floor(time / 60) % 60,
                hours = Math.floor(time / 3600);

            seconds = seconds < 10 ? `0${seconds}` : seconds;
            minutes = minutes < 10 ? `0${minutes}` : minutes;
            hours = hours < 10 ? `0${hours}` : hours;

            if (hours === 0 || hours === "00") {
                return `${minutes}:${seconds}`;
            }
            return `${hours}:${minutes}:${seconds}`;
        };

        if (videoTimeline) {
            videoTimeline.addEventListener("mousemove", e => {
                let timelineWidth = videoTimeline.clientWidth;
                let rect = videoTimeline.getBoundingClientRect();
                let offsetX = Math.max(0, Math.min(e.clientX - rect.left, timelineWidth));
                let percent = Math.floor((offsetX / timelineWidth) * (mainVideo.duration || 0));
                const progressTime = videoTimeline.querySelector("span");
                if (progressTime) {
                    progressTime.style.left = `${offsetX}px`;
                    progressTime.innerText = formatTime(percent);
                }
            });

            videoTimeline.addEventListener("click", e => {
                let timelineWidth = videoTimeline.clientWidth;
                let rect = videoTimeline.getBoundingClientRect();
                let offsetX = Math.max(0, Math.min(e.clientX - rect.left, timelineWidth));
                if (mainVideo.duration) {
                    mainVideo.currentTime = (offsetX / timelineWidth) * mainVideo.duration;
                }
            });

            const draggableProgressBar = e => {
                let timelineWidth = videoTimeline.clientWidth;
                let rect = videoTimeline.getBoundingClientRect();
                let offsetX = Math.max(0, Math.min(e.clientX - rect.left, timelineWidth));
                if (progressBar) progressBar.style.width = `${offsetX}px`;
                if (mainVideo.duration) {
                    mainVideo.currentTime = (offsetX / timelineWidth) * mainVideo.duration;
                }
                if (currentVidTime) currentVidTime.innerText = formatTime(mainVideo.currentTime);
            };

            videoTimeline.addEventListener("mousedown", () => videoTimeline.addEventListener("mousemove", draggableProgressBar));
            document.addEventListener("mouseup", () => videoTimeline.removeEventListener("mousemove", draggableProgressBar));
        }

        mainVideo.addEventListener("timeupdate", e => {
            let { currentTime, duration } = e.target;
            if (duration && progressBar) {
                let percent = (currentTime / duration) * 100;
                progressBar.style.width = `${percent}%`;
            }
            if (currentVidTime) currentVidTime.innerText = formatTime(currentTime);
        });

        mainVideo.addEventListener("loadeddata", () => {
            if (videoDuration) videoDuration.innerText = formatTime(mainVideo.duration);
        });

        if (volumeBtn && volumeSlider) {
            volumeBtn.addEventListener("click", () => {
                if (!volumeBtn.classList.contains("fa-volume-high")) {
                    mainVideo.volume = 0.5;
                    volumeBtn.classList.replace("fa-volume-xmark", "fa-volume-high");
                } else {
                    mainVideo.volume = 0.0;
                    volumeBtn.classList.replace("fa-volume-high", "fa-volume-xmark");
                }
                volumeSlider.value = mainVideo.volume;
            });

            volumeSlider.addEventListener("input", e => {
                mainVideo.volume = e.target.value;
                if (e.target.value == 0) {
                    volumeBtn.classList.replace("fa-volume-high", "fa-volume-xmark");
                } else {
                    volumeBtn.classList.replace("fa-volume-xmark", "fa-volume-high");
                }
            });
        }

        if (speedOptions && speedBtn) {
            speedOptions.querySelectorAll("li").forEach(option => {
                option.addEventListener("click", () => {
                    mainVideo.playbackRate = option.dataset.speed;
                    const activeOption = speedOptions.querySelector(".active");
                    if (activeOption) activeOption.classList.remove("active");
                    option.classList.add("active");
                });
            });

            document.addEventListener("click", e => {
                if (e.target.tagName !== "SPAN" || e.target.className !== "material-symbols-rounded") {
                    speedOptions.classList.remove("show");
                }
            });

            speedBtn.addEventListener("click", () => speedOptions.classList.toggle("show"));
        }

        if (pipBtn) pipBtn.addEventListener("click", () => mainVideo.requestPictureInPicture());

        if (skipBackward) skipBackward.addEventListener("click", () => mainVideo.currentTime -= 5);
        if (skipForward) skipForward.addEventListener("click", () => mainVideo.currentTime += 5);

        if (playPauseBtn) {
            mainVideo.addEventListener("play", () => playPauseBtn.classList.replace("fa-play", "fa-pause"));
            mainVideo.addEventListener("pause", () => playPauseBtn.classList.replace("fa-pause", "fa-play"));
            playPauseBtn.addEventListener("click", () => mainVideo.paused ? mainVideo.play() : mainVideo.pause());
        }

        if (fullScreenBtn) {
            fullScreenBtn.addEventListener("click", () => {
                container.classList.toggle("fullscreen");
                if (document.fullscreenElement) {
                    fullScreenBtn.classList.replace("fa-compress", "fa-expand");
                    return document.exitFullscreen();
                }
                fullScreenBtn.classList.replace("fa-expand", "fa-compress");
                container.requestFullscreen();
            });
        }
    }
}
