import { useDispatch } from "react-redux";
import { API_OPTION } from "../utils/constant";
import { addNowPlayingMovies, addupComingMovies } from "../rtk/movieSlice";
import { useEffect } from "react";

const useUpComing = () => {
  const dispatch = useDispatch();

  const getUpComing = async () => {
    const data = await fetch(
      "https://api.themoviedb.org/3/movie/upcoming",
      API_OPTION
    );
    const json = await data.json();

    dispatch(addupComingMovies(json.results));
  };

  useEffect(() => {
    getUpComing();
  }, []);
};

export default useUpComing;
