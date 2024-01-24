import React, { useEffect } from "react";
import { API_OPTION } from "../utils/constant";
import { useDispatch, useSelector } from "react-redux";
import { addMovietrailer } from "../rtk/movieSlice";
import useTrailerVideo from "../hooks/useTrailerVideo";

const VideoBacground = ({ moviesId }) => {
  useTrailerVideo(moviesId);

  const trailervideo = useSelector(store =>store.movies.movieTrailer)

  return (
    <div className=" w-screen">
      <iframe
        className="w-screen aspect-video"
        src={`https://www.youtube.com/embed/${trailervideo?.key}?&autoplay=1&mute=1`}
        title="YouTube video player"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
      ></iframe>
    </div>
  );
};

export default VideoBacground;
