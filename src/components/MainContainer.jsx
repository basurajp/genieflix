import React from "react";
import { useSelector } from "react-redux";
import VideoBacground from "./VideoBacground";
import VideoTitle from "./VideoTitle";

const MainContainer = () => {
  const movies = useSelector((store) => store?.movies?.nowPlayingMovies);
  if (!movies) return;
  const mainMovie = movies[3];
  const {title ,overview , id} = mainMovie



  return (
    <div>
      <VideoTitle title={title} overview={overview}  />
      <VideoBacground moviesId={id} />
    </div>
  );
};

export default MainContainer;
